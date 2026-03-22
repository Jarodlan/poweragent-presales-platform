from __future__ import annotations

from typing import Any

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


def _segment_texts(session: CustomerDemandSession) -> list[str]:
    values = []
    for item in session.segments.order_by("sequence_no", "created_at"):
        text = item.final_text or item.normalized_text or item.raw_text
        text = (text or "").strip()
        if text:
            values.append(text)
    return values


def build_stage_summary_payload(session: CustomerDemandSession) -> dict[str, Any]:
    texts = _segment_texts(session)
    if not texts:
        return {
            "current_topics": [],
            "confirmed_requirements": [],
            "pending_questions": [],
            "potential_directions": [],
            "risk_points": [],
        }

    current_topics = texts[:3]
    confirmed_requirements = texts[:5]
    pending_questions = [
        "客户预算、周期和实施边界是否明确",
        "客户当前已有数据与系统基础是否可用",
    ]
    potential_directions = [
        "进一步确认业务目标与量化指标",
        "进一步确认部署范围与组织角色分工",
    ]
    risk_points = [
        "当前沟通可能仍存在隐性需求未被显式表达",
        "若缺少数据基础，后续方案与实施节奏可能受影响",
    ]

    return {
        "current_topics": current_topics,
        "confirmed_requirements": confirmed_requirements,
        "pending_questions": pending_questions,
        "potential_directions": potential_directions,
        "risk_points": risk_points,
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
        llm_model="rule_based_mvp",
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


def build_final_report_payload(session: CustomerDemandSession) -> dict[str, Any]:
    texts = _segment_texts(session)
    summaries = list(session.stage_summaries.order_by("-summary_version")[:3])
    stage_points = []
    for item in summaries:
        stage_points.extend(item.summary_payload.get("confirmed_requirements", []))

    explicit_requirements = list(dict.fromkeys((texts[:6] + stage_points[:4])))[:8]
    implicit_requirements = [
        "客户可能希望提升需求沟通的结构化程度与内部协同效率",
        "客户可能关注后续方案形成、项目推进与实施可行性之间的衔接",
    ]
    constraints_and_risks = [
        "需求表达可能仍存在口语化和不完整问题，需要后续继续澄清",
        "若缺少现有系统、数据与组织边界信息，后续方案深度会受影响",
    ]
    pending_questions = [
        "客户希望优先解决的核心问题是什么",
        "客户对交付周期、预算与实施方式有哪些明确约束",
        "客户现有系统、数据和组织分工情况如何",
    ]
    next_actions = [
        "基于本次沟通内容形成内部需求复盘",
        "围绕待确认问题准备下一轮客户沟通提纲",
        "根据确认结果决定是否进入解决方案生成或 PoC 设计阶段",
    ]
    digging_directions = [
        "补问业务目标、量化指标与优先级",
        "补问现有系统、数据基础和部署边界",
        "补问项目预算、周期和成功标准",
    ]
    recommended_questions = [
        "当前最希望优先解决的问题是什么",
        "已有的系统和数据基础分别有哪些",
        "希望项目最终达到哪些业务或管理效果",
    ]

    return {
        "summary": f"本次沟通围绕“{session.topic or session.session_title}”展开，已经形成初步需求理解和待确认问题清单。",
        "current_problem": texts[:3],
        "explicit_requirements": explicit_requirements,
        "implicit_requirements": implicit_requirements,
        "constraints_and_risks": constraints_and_risks,
        "pending_questions": pending_questions,
        "next_actions": next_actions,
        "digging_directions": digging_directions,
        "recommended_questions": recommended_questions,
    }


def build_final_report_markdown(session: CustomerDemandSession, payload: dict[str, Any]) -> tuple[str, str, str]:
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
        llm_model="rule_based_mvp",
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

