from __future__ import annotations

import json
import re
import threading
from typing import Any

import requests
from requests import HTTPError
from django.db import close_old_connections
from django.conf import settings
from django.utils import timezone

from .models import (
    CustomerDemandAnalysisTask,
    CustomerDemandReport,
    CustomerDemandSession,
    CustomerDemandStageSummary,
)


def resolve_visible_customer_demand_sessions(user):
    qs = CustomerDemandSession.objects.select_related("owner", "department")
    if user.is_superuser:
        return qs
    return qs.filter(owner=user)


def _update_task(
    task: CustomerDemandAnalysisTask,
    *,
    status: str | None = None,
    current_step: str | None = None,
    current_step_label: str | None = None,
    progress: int | None = None,
    result_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
    finished: bool = False,
):
    fields: list[str] = ["updated_at"]
    if status is not None:
        task.status = status
        fields.append("status")
    if current_step is not None:
        task.current_step = current_step
        fields.append("current_step")
    if current_step_label is not None:
        task.current_step_label = current_step_label
        fields.append("current_step_label")
    if progress is not None:
        task.progress = progress
        fields.append("progress")
    if result_payload is not None:
        task.result_payload = result_payload
        fields.append("result_payload")
    if error_message is not None:
        task.error_message = error_message
        fields.append("error_message")
    if finished:
        task.finished_at = timezone.now()
        fields.append("finished_at")
    task.save(update_fields=fields)


def _accepted_segments(session: CustomerDemandSession):
    return session.segments.filter(segment_status="normalized", review_flag=False).order_by("sequence_no", "created_at")


def _review_segments(session: CustomerDemandSession):
    return session.segments.filter(review_flag=True).order_by("sequence_no", "created_at")


def _segment_texts(session: CustomerDemandSession, *, accepted_only: bool = True) -> list[str]:
    values = []
    queryset = _accepted_segments(session) if accepted_only else session.segments.order_by("sequence_no", "created_at")
    for item in queryset:
        text = item.final_text or item.normalized_text or item.raw_text
        text = (text or "").strip()
        if text:
            values.append(text)
    return values


def _llm_client_config() -> tuple[str, str, str]:
    return (
        getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_BASE_URL", ""),
        getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_API_KEY", ""),
        getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_MODEL", "qwen-plus"),
    )


def _extract_json_block(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _call_qwen_json(system_prompt: str, user_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    base_url, api_key, model = _llm_client_config()
    if not base_url or not api_key:
        return {}, "unconfigured"

    def _send(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
        parsed = _extract_json_block(content)
        if not parsed:
            raise ValueError("Qwen 返回未能解析为 JSON")
        return parsed, model

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "stream": False,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
    }
    try:
        return _send(payload)
    except HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code != 400:
            raise
        fallback_payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt + " 仅返回一个合法 JSON 对象，不要使用 markdown 代码块，不要输出解释文字。",
                },
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "stream": False,
            "max_tokens": 1600,
        }
        try:
            return _send(fallback_payload)
        except Exception as inner_exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = (exc.response.text or "")[:300]
            raise ValueError(f"Qwen JSON 调用失败: {inner_exc}; upstream={detail}") from inner_exc


def _call_qwen_markdown(system_prompt: str, user_payload: dict[str, Any]) -> tuple[str, str]:
    base_url, api_key, model = _llm_client_config()
    if not base_url or not api_key:
        return "", "unconfigured"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "stream": False,
        "max_tokens": 2600,
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
    text = content.strip()
    if not text:
        raise ValueError("Qwen 返回空白 Markdown")
    return text, model


def _compact_text(text: str, limit: int = 360) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    head = cleaned[: int(limit * 0.75)].rstrip("，。；,; ")
    tail = cleaned[-int(limit * 0.2) :].lstrip("，。；,; ")
    return f"{head}……{tail}"


def _keyword_signal_summary(session: CustomerDemandSession, texts: list[str]) -> dict[str, list[str]]:
    joined = " ".join(texts)
    topic_name = session.topic or session.session_title or "客户需求沟通"
    current_topics: list[str] = [f"本轮沟通重点围绕“{topic_name}”展开。"]
    confirmed_requirements: list[str] = []
    pending_questions: list[str] = []
    potential_directions: list[str] = []
    risk_points: list[str] = []

    def add_once(target: list[str], item: str):
        if item not in target:
            target.append(item)

    if any(word in joined for word in ["光伏", "弃电", "消纳"]):
        add_once(current_topics, "客户重点关注园区光伏发电消纳不足与弃电浪费问题。")
        add_once(confirmed_requirements, "需要识别并优化园区内光伏发电的本地消纳路径，降低弃电比例。")
    if any(word in joined for word in ["储能", "放电", "充放电", "调度"]):
        add_once(current_topics, "客户希望提升储能系统充放电调度的时序合理性与自动化水平。")
        add_once(confirmed_requirements, "希望系统根据负荷、电价与新能源出力自动优化储能充放电策略。")
    if any(word in joined for word in ["峰谷", "电价", "套利", "收益"]):
        add_once(confirmed_requirements, "客户明确关注峰谷套利收益稳定性，希望收益测算更透明。")
        add_once(potential_directions, "后续可继续挖掘电价响应策略、收益评估模型和运营报表需求。")
    if any(word in joined for word in ["运维", "上手", "三个人", "手机端"]):
        add_once(confirmed_requirements, "客户希望系统易于上手，能够在运维人员有限的情况下保持稳定运行。")
        add_once(potential_directions, "可进一步确认移动端使用、告警分发和远程运维支撑需求。")
    if any(word in joined for word in ["预算", "投入", "回本", "服务费"]):
        add_once(confirmed_requirements, "客户关注项目投入方式、资金压力与回本周期，希望提供灵活的合作模式。")
        add_once(pending_questions, "需进一步明确预算区间、投资决策机制和可接受回本周期。")
    if any(word in joined for word in ["免费", "诊断", "上门"]):
        add_once(potential_directions, "可安排现场诊断或试算评估，帮助客户在正式立项前判断实施价值。")

    add_once(pending_questions, "客户当前已接入的光伏、储能、负荷和计量数据范围是否完整可用。")
    add_once(pending_questions, "客户希望优先优化的目标是降本、消纳提升、运行安全，还是综合收益。")
    add_once(risk_points, "如果现有数据质量不足或设备接口不统一，后续分析深度与落地周期会受影响。")
    add_once(risk_points, "如果客户预算、合作模式和验收指标未明确，后续方案边界容易反复调整。")

    if len(current_topics) == 1:
        add_once(current_topics, "当前沟通已形成较明确的业务主题，但仍需继续压实量化目标和实施边界。")
    if not confirmed_requirements:
        add_once(confirmed_requirements, "客户已表达出对业务问题识别、收益优化和系统易用性的综合诉求。")
    if not potential_directions:
        add_once(potential_directions, "建议继续挖掘业务目标量化指标、现有数据基础和项目实施节奏。")

    return {
        "current_topics": current_topics[:4],
        "confirmed_requirements": confirmed_requirements[:6],
        "pending_questions": pending_questions[:5],
        "potential_directions": potential_directions[:4],
        "risk_points": risk_points[:4],
    }


def _accepted_segment_records(session: CustomerDemandSession) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in _accepted_segments(session):
        text = (item.final_text or item.normalized_text or item.raw_text or "").strip()
        if not text:
            continue
        records.append(
            {
                "sequence_no": item.sequence_no,
                "speaker_label": item.speaker_label or "未标注",
                "text": _compact_text(text, 420),
                "semantic_score": float(item.semantic_score) if item.semantic_score is not None else None,
            }
        )
    return records


def _review_segment_records(session: CustomerDemandSession) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in _review_segments(session):
        text = (item.final_text or item.normalized_text or item.raw_text or "").strip()
        if not text:
            continue
        records.append(
            {
                "sequence_no": item.sequence_no,
                "speaker_label": item.speaker_label or "未标注",
                "text": _compact_text(text, 240),
                "segment_status": item.segment_status,
                "issues": item.issues_json or [],
                "semantic_score": float(item.semantic_score) if item.semantic_score is not None else None,
            }
        )
    return records


def _safe_list(parsed: dict[str, Any], key: str, default: list[str] | None = None) -> list[str]:
    value = parsed.get(key)
    if not isinstance(value, list):
        return default or []
    return [str(item).strip() for item in value if str(item).strip()]


def build_stage_summary_payload(session: CustomerDemandSession) -> dict[str, Any]:
    accepted_records = _accepted_segment_records(session)
    review_records = _review_segment_records(session)
    if accepted_records:
        try:
            parsed, model = _call_qwen_json(
                (
                    "你是企业级客户需求分析助手中的阶段整理模块。"
                    "请基于已经通过语义校验的沟通分段，抽取结构化阶段整理。"
                    "要求输出高价值分析，不要粘贴原始大段口语，不要逐字复述客户原话。"
                    "每个条目尽量控制在一到两句话内，优先写抽象后的需求点、约束、疑问和风险。"
                ),
                {
                    "session_context": {
                        "customer_name": session.customer_name,
                        "session_title": session.session_title,
                        "industry": session.industry,
                        "region": session.region,
                        "topic": session.topic,
                        "remarks": session.remarks,
                    },
                    "accepted_segments": accepted_records[:8],
                    "review_segments": review_records,
                    "output_schema": {
                        "current_topics": ["当前核心讨论主题，2-4条"],
                        "confirmed_requirements": ["已明确需求点，3-6条"],
                        "pending_questions": ["仍需补问的问题，3-5条"],
                        "potential_directions": ["后续可继续挖掘的方向，2-4条"],
                        "risk_points": ["当前风险与约束，2-4条"],
                        "semantic_warnings": ["待复核内容的提醒，0-3条"],
                    },
                },
            )
            return {
                "current_topics": _safe_list(parsed, "current_topics"),
                "confirmed_requirements": _safe_list(parsed, "confirmed_requirements"),
                "pending_questions": _safe_list(parsed, "pending_questions"),
                "potential_directions": _safe_list(parsed, "potential_directions"),
                "risk_points": _safe_list(parsed, "risk_points"),
                "semantic_warnings": _safe_list(parsed, "semantic_warnings"),
                "_llm_model": model,
            }
        except Exception as exc:
            llm_error = str(exc)
        else:
            llm_error = ""
    else:
        llm_error = ""

    texts = _segment_texts(session, accepted_only=True)
    review_texts = _segment_texts(session, accepted_only=False)
    if not texts:
        texts = review_texts[:3]
    if not texts:
        return {
            "current_topics": [],
            "confirmed_requirements": [],
            "pending_questions": [],
            "potential_directions": [],
            "risk_points": [],
            "semantic_warnings": [],
        }

    inferred = _keyword_signal_summary(session, texts)
    current_topics = inferred["current_topics"]
    confirmed_requirements = inferred["confirmed_requirements"]
    pending_questions = inferred["pending_questions"]
    potential_directions = inferred["potential_directions"]
    risk_points = inferred["risk_points"]
    semantic_warnings = []
    for item in _review_segments(session)[:3]:
        preview = (item.final_text or item.normalized_text or item.raw_text or "").strip()[:80]
        if preview:
            semantic_warnings.append(f"存在待复核分段：{preview}")

    return {
        "current_topics": current_topics,
        "confirmed_requirements": confirmed_requirements,
        "pending_questions": pending_questions,
        "potential_directions": potential_directions,
        "risk_points": risk_points,
        "semantic_warnings": semantic_warnings,
        "_llm_model": "rule_based_mvp",
        "_llm_error": llm_error,
    }


def build_stage_summary_markdown(payload: dict[str, Any]) -> str:
    def section(title: str, items: list[str]) -> str:
        if not items:
            return f"### {title}\n- 暂无\n"
        return "### " + title + "\n" + "\n".join(f"- {item}" for item in items) + "\n"

    return "\n".join(
        [
            section("当前讨论主题", payload.get("current_topics", [])),
            section("已确认需求", payload.get("confirmed_requirements", [])),
            section("待确认问题", payload.get("pending_questions", [])),
            section("潜在方向", payload.get("potential_directions", [])),
            section("风险点", payload.get("risk_points", [])),
            section("语义复核提醒", payload.get("semantic_warnings", [])),
        ]
    ).strip()


def create_stage_summary(*, session: CustomerDemandSession, trigger_type: str, created_by) -> tuple[CustomerDemandAnalysisTask, CustomerDemandStageSummary]:
    task = CustomerDemandAnalysisTask.objects.create(
        session=session,
        task_type="stage_summary",
        status="running",
        current_step="build_stage_summary",
        current_step_label="生成阶段整理",
        progress=15,
        request_payload={"trigger_type": trigger_type},
        started_by=created_by,
        started_at=timezone.now(),
    )

    payload = build_stage_summary_payload(session)
    markdown = build_stage_summary_markdown(payload)
    version = session.latest_stage_version + 1
    segments = session.segments.order_by("sequence_no")
    first_segment = segments.first()
    last_segment = segments.last()
    summary = CustomerDemandStageSummary.objects.create(
        session=session,
        summary_version=version,
        trigger_type=trigger_type,
        covered_segment_start=first_segment.sequence_no if first_segment else 1,
        covered_segment_end=last_segment.sequence_no if last_segment else 1,
        summary_markdown=markdown,
        summary_payload=payload,
        llm_model=payload.get("_llm_model", "rule_based_mvp"),
        created_by=created_by,
    )

    session.latest_stage_version = version
    session.save(update_fields=["latest_stage_version", "updated_at"])

    task.status = "completed"
    task.current_step = "stage_summary_completed"
    task.current_step_label = "阶段整理完成"
    task.progress = 100
    task.result_payload = {"summary_id": str(summary.id), "summary_version": version}
    task.finished_at = timezone.now()
    task.save(
        update_fields=[
            "status",
            "current_step",
            "current_step_label",
            "progress",
            "result_payload",
            "finished_at",
            "updated_at",
        ]
    )
    return task, summary


def _run_stage_summary_task(task_id: str):
    close_old_connections()
    try:
        task = CustomerDemandAnalysisTask.objects.select_related("session", "started_by").get(id=task_id)
        session = task.session
        _update_task(
            task,
            status="running",
            current_step="build_stage_summary_payload",
            current_step_label="抽取结构化阶段要点",
            progress=28,
        )
        payload = build_stage_summary_payload(session)
        _update_task(
            task,
            current_step="render_stage_summary_markdown",
            current_step_label="整理阶段输出内容",
            progress=68,
        )
        markdown = build_stage_summary_markdown(payload)
        version = session.latest_stage_version + 1
        segments = session.segments.order_by("sequence_no")
        first_segment = segments.first()
        last_segment = segments.last()
        summary = CustomerDemandStageSummary.objects.create(
            session=session,
            summary_version=version,
            trigger_type=task.request_payload.get("trigger_type", "manual"),
            covered_segment_start=first_segment.sequence_no if first_segment else 1,
            covered_segment_end=last_segment.sequence_no if last_segment else 1,
            summary_markdown=markdown,
            summary_payload=payload,
            llm_model=payload.get("_llm_model", "rule_based_mvp"),
            created_by=task.started_by,
        )
        session.latest_stage_version = version
        session.save(update_fields=["latest_stage_version", "updated_at"])
        _update_task(
            task,
            status="completed",
            current_step="stage_summary_completed",
            current_step_label="阶段整理完成",
            progress=100,
            result_payload={"summary_id": str(summary.id), "summary_version": version},
            finished=True,
        )
    except Exception as exc:
        task = CustomerDemandAnalysisTask.objects.filter(id=task_id).first()
        if task:
            _update_task(
                task,
                status="failed",
                current_step="stage_summary_failed",
                current_step_label="阶段整理失败",
                progress=100,
                error_message=str(exc),
                finished=True,
            )
    finally:
        close_old_connections()


def enqueue_stage_summary(*, session: CustomerDemandSession, trigger_type: str, created_by) -> CustomerDemandAnalysisTask:
    task = CustomerDemandAnalysisTask.objects.create(
        session=session,
        task_type="stage_summary",
        status="queued",
        current_step="queue_stage_summary",
        current_step_label="阶段整理排队中",
        progress=5,
        request_payload={"trigger_type": trigger_type},
        started_by=created_by,
        started_at=timezone.now(),
    )
    threading.Thread(target=_run_stage_summary_task, args=(str(task.id),), daemon=True).start()
    return task


def build_final_report_payload(session: CustomerDemandSession) -> dict[str, Any]:
    accepted_records = _accepted_segment_records(session)
    review_records = _review_segment_records(session)
    latest_summary = session.stage_summaries.order_by("-summary_version", "-created_at").first()
    if accepted_records:
        try:
            parsed, model = _call_qwen_json(
                (
                    "你是企业级客户需求分析助手中的正式报告生成模块。"
                    "请根据通过语义校验的沟通分段和阶段整理，生成结构化需求分析结果。"
                    "你的输出必须是分析结论，不要大段照抄客户原始口语。"
                    "如果原始信息不完整，也要明确指出待确认项，而不是用原文填充。"
                ),
                {
                    "session_context": {
                        "customer_name": session.customer_name,
                        "session_title": session.session_title,
                        "industry": session.industry,
                        "region": session.region,
                        "topic": session.topic,
                        "remarks": session.remarks,
                    },
                    "accepted_segments": accepted_records[:8],
                    "review_segments": review_records,
                    "latest_stage_summary": latest_summary.summary_payload if latest_summary else {},
                    "output_schema": {
                        "summary": "1-2句整体判断",
                        "current_problem": ["客户当前问题概述，2-4条"],
                        "explicit_requirements": ["已明确需求，4-8条"],
                        "implicit_requirements": ["隐性诉求，2-4条"],
                        "constraints_and_risks": ["约束与风险，2-5条"],
                        "pending_questions": ["待确认问题，3-6条"],
                        "next_actions": ["建议下一步动作，3-5条"],
                        "digging_directions": ["需求挖掘方向，3-5条"],
                        "recommended_questions": ["推荐追问问题，3-6条"],
                        "semantic_warnings": ["待复核提醒，0-4条"],
                    },
                },
            )
            return {
                "summary": str(parsed.get("summary") or f"本次沟通围绕“{session.topic or session.session_title}”展开，已经形成初步需求理解和待确认问题清单。").strip(),
                "current_problem": _safe_list(parsed, "current_problem"),
                "explicit_requirements": _safe_list(parsed, "explicit_requirements"),
                "implicit_requirements": _safe_list(parsed, "implicit_requirements"),
                "constraints_and_risks": _safe_list(parsed, "constraints_and_risks"),
                "pending_questions": _safe_list(parsed, "pending_questions"),
                "next_actions": _safe_list(parsed, "next_actions"),
                "digging_directions": _safe_list(parsed, "digging_directions"),
                "recommended_questions": _safe_list(parsed, "recommended_questions"),
                "semantic_warnings": _safe_list(parsed, "semantic_warnings"),
                "_llm_model": model,
            }
        except Exception as exc:
            llm_error = str(exc)
        else:
            llm_error = ""
    else:
        llm_error = ""

    texts = _segment_texts(session, accepted_only=True)
    review_segments = _review_segments(session)
    if not texts:
        texts = _segment_texts(session, accepted_only=False)
    summaries = list(session.stage_summaries.order_by("-summary_version")[:3])
    stage_points = []
    for item in summaries:
        stage_points.extend(item.summary_payload.get("confirmed_requirements", []))

    inferred = _keyword_signal_summary(session, texts)
    explicit_requirements = list(dict.fromkeys((inferred["confirmed_requirements"] + stage_points[:4])))[:8]
    implicit_requirements = [
        "客户希望在不明显增加运维负担的前提下，让系统具备可持续运行和可复制推广能力。",
        "客户除了关注当前问题解决外，也在意后续合作模式、投入压力和项目落地确定性。",
    ]
    constraints_and_risks = inferred["risk_points"][:]
    pending_questions = inferred["pending_questions"][:]
    next_actions = [
        "基于本次沟通内容形成内部复盘纪要，并明确需要补问的关键问题。",
        "准备面向客户的下一轮沟通提纲，补齐预算、数据基础和实施边界信息。",
        "在信息进一步明确后，决定是否进入解决方案设计、试算评估或 PoC 阶段。",
    ]
    digging_directions = [
        "继续挖掘量化业务目标，例如弃电降低比例、套利收益提升幅度和运维效率改善目标。",
        "进一步确认数据接入基础、设备接口条件和现场实施约束。",
        "结合客户预算和合作模式，评估项目切入路径与阶段性交付方式。",
    ]
    recommended_questions = [
        "当前最希望优先优化的业务目标是什么，是否有量化指标？",
        "现有光伏、储能、负荷和电价数据是否已经具备统一接入条件？",
        "对于投入方式、收益分配和回本周期，客户目前的接受边界是什么？",
    ]
    semantic_warnings = []
    for item in review_segments[:5]:
        preview = (item.final_text or item.normalized_text or item.raw_text or "").strip()[:100]
        if preview:
            semantic_warnings.append(preview)

    return {
        "summary": f"本次沟通围绕“{session.topic or session.session_title}”展开，已经形成初步需求理解和待确认问题清单。",
        "current_problem": inferred["current_topics"][:3],
        "explicit_requirements": explicit_requirements,
        "implicit_requirements": implicit_requirements,
        "constraints_and_risks": constraints_and_risks,
        "pending_questions": pending_questions,
        "next_actions": next_actions,
        "digging_directions": digging_directions,
        "recommended_questions": recommended_questions,
        "semantic_warnings": semantic_warnings,
        "_llm_model": "rule_based_mvp",
        "_llm_error": llm_error,
    }


def build_final_report_markdown(session: CustomerDemandSession, payload: dict[str, Any]) -> tuple[str, str, str]:
    if payload.get("_llm_model") and payload.get("_llm_model") != "rule_based_mvp":
        try:
            report_markdown, _ = _call_qwen_markdown(
                (
                    "你是企业级客户需求分析智能体的正式报告撰写模块。"
                    "请基于已经结构化的需求分析结果，输出一份专业、简洁、分析型 Markdown 报告。"
                    "不要照抄原始客户对话，不要输出口语化原文大段转写。"
                    "请严格使用以下二级标题："
                    "沟通背景与上下文、当前问题概述、已明确需求、隐性需求与潜在诉求、约束条件与风险点、语义复核提醒、待确认问题清单、建议下一步动作。"
                    "每个部分优先用条目表达，语言要像内部售前/需求分析文档。"
                ),
                {
                    "customer_name": session.customer_name,
                    "session_title": session.session_title,
                    "industry": session.industry,
                    "region": session.region,
                    "analysis_payload": {
                        "summary": payload.get("summary", ""),
                        "current_problem": payload.get("current_problem", []),
                        "explicit_requirements": payload.get("explicit_requirements", []),
                        "implicit_requirements": payload.get("implicit_requirements", []),
                        "constraints_and_risks": payload.get("constraints_and_risks", []),
                        "semantic_warnings": payload.get("semantic_warnings", []),
                        "pending_questions": payload.get("pending_questions", []),
                        "next_actions": payload.get("next_actions", []),
                    },
                },
            )
            digging = "\n".join(
                ["## 需求挖掘方向建议", *(f"- {item}" for item in payload.get("digging_directions", []))]
            ).strip()
            questions = "\n".join(
                ["## 建议补问问题", *(f"- {item}" for item in payload.get("recommended_questions", []))]
            ).strip()
            return report_markdown.strip(), digging, questions
        except Exception:
            pass

    report = "\n".join(
        [
            f"# {session.customer_name}需求分析报告",
            "",
            "## 沟通背景与上下文",
            f"- 客户名称：{session.customer_name}",
            f"- 会话主题：{session.session_title}",
            f"- 行业：{session.industry or '未指定'}",
            f"- 地区：{session.region or '未指定'}",
            "",
            "## 当前问题概述",
            *(f"- {item}" for item in payload.get("current_problem", [])),
            "",
            "## 已明确需求",
            *(f"- {item}" for item in payload.get("explicit_requirements", [])),
            "",
            "## 隐性需求与潜在诉求",
            *(f"- {item}" for item in payload.get("implicit_requirements", [])),
            "",
            "## 约束条件与风险点",
            *(f"- {item}" for item in payload.get("constraints_and_risks", [])),
            "",
            "## 语义复核提醒",
            *(f"- {item}" for item in payload.get("semantic_warnings", [])),
            "",
            "## 待确认问题清单",
            *(f"- {item}" for item in payload.get("pending_questions", [])),
            "",
            "## 建议下一步动作",
            *(f"- {item}" for item in payload.get("next_actions", [])),
        ]
    ).strip()

    digging = "\n".join(
        ["## 需求挖掘方向建议", *(f"- {item}" for item in payload.get("digging_directions", []))]
    ).strip()
    questions = "\n".join(
        ["## 建议补问问题", *(f"- {item}" for item in payload.get("recommended_questions", []))]
    ).strip()
    return report, digging, questions


def create_final_report(*, session: CustomerDemandSession, created_by, knowledge_enabled: bool) -> tuple[CustomerDemandAnalysisTask, CustomerDemandReport]:
    task = CustomerDemandAnalysisTask.objects.create(
        session=session,
        task_type="final_analysis",
        status="running",
        current_step="build_final_report",
        current_step_label="生成需求分析报告",
        progress=20,
        request_payload={"knowledge_enabled": knowledge_enabled},
        started_by=created_by,
        started_at=timezone.now(),
    )

    payload = build_final_report_payload(session)
    report_markdown, digging_markdown, questions_markdown = build_final_report_markdown(session, payload)
    version = (session.reports.order_by("-report_version").first().report_version + 1) if session.reports.exists() else 1
    report = CustomerDemandReport.objects.create(
        session=session,
        report_version=version,
        report_title=f"{session.customer_name}需求分析报告",
        report_markdown=report_markdown,
        report_payload=payload,
        digging_suggestions_markdown=digging_markdown,
        digging_suggestions_payload={"items": payload.get("digging_directions", [])},
        recommended_questions_markdown=questions_markdown,
        knowledge_enabled=knowledge_enabled,
        used_knowledge_sources=[],
        llm_model=payload.get("_llm_model", "rule_based_mvp"),
        status="completed",
        created_by=created_by,
    )

    session.status = "completed"
    session.analysis_started_at = session.analysis_started_at or timezone.now()
    session.analysis_finished_at = timezone.now()
    session.knowledge_enabled = knowledge_enabled
    session.save(update_fields=["status", "analysis_started_at", "analysis_finished_at", "knowledge_enabled", "updated_at"])

    task.status = "completed"
    task.current_step = "final_report_completed"
    task.current_step_label = "需求分析完成"
    task.progress = 100
    task.result_payload = {"report_id": str(report.id), "report_version": version}
    task.finished_at = timezone.now()
    task.save(
        update_fields=[
            "status",
            "current_step",
            "current_step_label",
            "progress",
            "result_payload",
            "finished_at",
            "updated_at",
        ]
    )
    return task, report


def _run_final_report_task(task_id: str):
    close_old_connections()
    try:
        task = CustomerDemandAnalysisTask.objects.select_related("session", "started_by").get(id=task_id)
        session = task.session
        session.status = "analyzing"
        session.analysis_started_at = session.analysis_started_at or timezone.now()
        session.save(update_fields=["status", "analysis_started_at", "updated_at"])
        _update_task(
            task,
            status="running",
            current_step="build_final_report_payload",
            current_step_label="分析客户需求与风险约束",
            progress=32,
        )
        payload = build_final_report_payload(session)
        _update_task(
            task,
            current_step="render_final_report_markdown",
            current_step_label="生成正式需求分析报告",
            progress=76,
        )
        report_markdown, digging_markdown, questions_markdown = build_final_report_markdown(session, payload)
        version = (session.reports.order_by("-report_version").first().report_version + 1) if session.reports.exists() else 1
        report = CustomerDemandReport.objects.create(
            session=session,
            report_version=version,
            report_title=f"{session.customer_name}需求分析报告",
            report_markdown=report_markdown,
            report_payload=payload,
            digging_suggestions_markdown=digging_markdown,
            digging_suggestions_payload={"items": payload.get("digging_directions", [])},
            recommended_questions_markdown=questions_markdown,
            knowledge_enabled=bool(task.request_payload.get("knowledge_enabled", False)),
            used_knowledge_sources=[],
            llm_model=payload.get("_llm_model", "rule_based_mvp"),
            status="completed",
            created_by=task.started_by,
        )
        session.status = "completed"
        session.analysis_finished_at = timezone.now()
        session.knowledge_enabled = bool(task.request_payload.get("knowledge_enabled", False))
        session.save(update_fields=["status", "analysis_finished_at", "knowledge_enabled", "updated_at"])
        _update_task(
            task,
            status="completed",
            current_step="final_report_completed",
            current_step_label="需求分析完成",
            progress=100,
            result_payload={"report_id": str(report.id), "report_version": version},
            finished=True,
        )
    except Exception as exc:
        task = CustomerDemandAnalysisTask.objects.filter(id=task_id).select_related("session").first()
        if task:
            task.session.status = "failed"
            task.session.analysis_finished_at = timezone.now()
            task.session.save(update_fields=["status", "analysis_finished_at", "updated_at"])
            _update_task(
                task,
                status="failed",
                current_step="final_report_failed",
                current_step_label="需求分析失败",
                progress=100,
                error_message=str(exc),
                finished=True,
            )
    finally:
        close_old_connections()


def enqueue_final_report(*, session: CustomerDemandSession, created_by, knowledge_enabled: bool) -> CustomerDemandAnalysisTask:
    task = CustomerDemandAnalysisTask.objects.create(
        session=session,
        task_type="final_analysis",
        status="queued",
        current_step="queue_final_report",
        current_step_label="需求分析任务排队中",
        progress=5,
        request_payload={"knowledge_enabled": knowledge_enabled},
        started_by=created_by,
        started_at=timezone.now(),
    )
    threading.Thread(target=_run_final_report_task, args=(str(task.id),), daemon=True).start()
    return task
