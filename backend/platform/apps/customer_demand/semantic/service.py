from __future__ import annotations

import json
import re
from typing import Any

import requests
from django.conf import settings

from ..models import CustomerDemandSegment, CustomerDemandSession
from .types import SemanticValidationResult


def _recent_valid_texts(session: CustomerDemandSession, exclude_segment_id=None) -> list[str]:
    values: list[str] = []
    qs = session.segments.order_by("sequence_no", "created_at")
    if exclude_segment_id:
        qs = qs.exclude(id=exclude_segment_id)
    for item in qs:
        text = (item.final_text or item.normalized_text or item.raw_text or "").strip()
        if not text:
            continue
        if item.segment_status == "normalized" and not item.review_flag:
            values.append(text)
    return values[-5:]


def _build_session_context(session: CustomerDemandSession, segment: CustomerDemandSegment) -> dict[str, Any]:
    return {
        "customer_name": session.customer_name,
        "session_title": session.session_title,
        "industry": session.industry,
        "region": session.region,
        "topic": session.topic,
        "remarks": session.remarks,
        "recent_valid_segments": _recent_valid_texts(session, exclude_segment_id=segment.id),
    }


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


def _keyword_tokens(text: str) -> list[str]:
    raw_parts = re.split(r"[，。！？；、,.!?\s:：（）()]+", text or "")
    tokens: list[str] = []
    for item in raw_parts:
        value = item.strip()
        if len(value) >= 2:
            tokens.append(value)
    return tokens


def _heuristic_validate(session: CustomerDemandSession, segment: CustomerDemandSegment) -> SemanticValidationResult:
    text = (segment.final_text or segment.normalized_text or segment.raw_text or "").strip()
    context_text = " ".join(
        filter(
            None,
            [
                session.session_title,
                session.topic,
                session.customer_name,
                session.industry,
                session.region,
                session.remarks,
            ],
        )
    )
    context_tokens = set(_keyword_tokens(context_text))
    text_tokens = set(_keyword_tokens(text))
    overlap = len(context_tokens & text_tokens)
    score = 0.2
    if text_tokens:
        score = min(1.0, overlap / max(len(text_tokens), 6) * 3)

    decision = "accept"
    issues: list[str] = []
    if score < 0.15:
        decision = "review_required"
        issues.append("当前分段与会话主题相关性较弱，建议人工复核")
    payload = {
        "provider": "heuristic_semantic",
        "matched_tokens": sorted(context_tokens & text_tokens)[:12],
        "context_tokens": sorted(context_tokens)[:20],
        "reasoning": "使用关键词交集对当前分段和会话主题进行启发式相关性判断。",
    }
    return SemanticValidationResult(
        decision=decision,
        score=round(score, 4),
        normalized_text=text,
        issues=issues,
        payload=payload,
    )


def _qwen_validate(session: CustomerDemandSession, segment: CustomerDemandSegment) -> SemanticValidationResult:
    base_url = getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_BASE_URL", "") or getattr(settings, "CUSTOMER_DEMAND_QWEN_ASR_BASE_URL", "")
    api_key = getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_API_KEY", "") or getattr(settings, "CUSTOMER_DEMAND_QWEN_ASR_API_KEY", "")
    model = getattr(settings, "CUSTOMER_DEMAND_QWEN_LLM_MODEL", "qwen-plus")
    if not base_url or not api_key:
        return _heuristic_validate(session, segment)

    segment_text = (segment.final_text or segment.normalized_text or segment.raw_text or "").strip()
    if not segment_text:
        return SemanticValidationResult(
            decision="review_required",
            score=0.0,
            normalized_text="",
            issues=["空白分段无法进行语义校验"],
            payload={"provider": "qwen_semantic", "model": model},
        )

    context = _build_session_context(session, segment)
    system_prompt = (
        "你是电力行业客户需求分析智能体中的语义校验模块。"
        "你的任务是判断当前分段内容是否属于本次客户沟通会话主题，"
        "并给出严格的 JSON 输出。"
        "只输出 JSON，不要输出解释。"
    )
    user_prompt = {
        "session_context": context,
        "segment_text": segment_text,
        "output_schema": {
            "decision": "accept|review_required|discard",
            "semantic_score": "0到1的小数",
            "normalized_text": "保留原意的轻度整理文本",
            "issues": ["若需复核，列出原因"],
            "matched_topics": ["当前分段命中的主题关键词"],
            "reasoning": "简短说明",
        },
        "decision_rules": [
            "如果内容与当前会话主题高度一致，则 accept",
            "如果内容混入另一个明显不同的话题，或无法确定是否属于当前主题，则 review_required",
            "如果内容明显是无意义噪声、闲聊且对需求分析无价值，则 discard",
            "不要为了通过而强行 accept",
        ],
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        result = _heuristic_validate(session, segment)
        result.issues.append(f"Qwen 语义校验失败，已使用启发式兜底: {exc}")
        result.payload["fallback_reason"] = str(exc)
        return result

    choice = ((data.get("choices") or [{}])[0]) if isinstance(data, dict) else {}
    message = choice.get("message") or {}
    content = (message.get("content") or "").strip()
    parsed = _extract_json_block(content)
    if not parsed:
        result = _heuristic_validate(session, segment)
        result.issues.append("Qwen 语义校验返回不可解析，已使用启发式兜底")
        result.payload["fallback_reason"] = "invalid_json"
        return result

    decision = str(parsed.get("decision") or "review_required").strip()
    if decision not in {"accept", "review_required", "discard"}:
        decision = "review_required"
    score = parsed.get("semantic_score")
    try:
        score = None if score is None else float(score)
    except (TypeError, ValueError):
        score = None

    issues = [str(item) for item in (parsed.get("issues") or []) if str(item).strip()]
    normalized_text = str(parsed.get("normalized_text") or segment_text).strip()
    semantic_payload = {
        "provider": "qwen_semantic",
        "model": model,
        "matched_topics": parsed.get("matched_topics") or [],
        "reasoning": parsed.get("reasoning") or "",
        "request_id": data.get("id"),
    }
    return SemanticValidationResult(
        decision=decision,
        score=score,
        normalized_text=normalized_text,
        issues=issues,
        payload=semantic_payload,
    )


def validate_segment_semantics(session: CustomerDemandSession, segment: CustomerDemandSegment) -> CustomerDemandSegment:
    result = _qwen_validate(session, segment)
    current_issues = [str(item) for item in (segment.issues_json or []) if str(item).strip()]
    merged_issues = list(dict.fromkeys(current_issues + result.issues))

    final_text = result.normalized_text or segment.final_text or segment.normalized_text or segment.raw_text
    segment.normalized_text = result.normalized_text or segment.normalized_text or segment.raw_text
    segment.final_text = final_text
    segment.semantic_score = result.score
    segment.semantic_payload = result.payload
    segment.llm_provider = result.payload.get("provider", "")

    if result.decision == "discard":
        segment.segment_status = "discarded"
        segment.review_flag = True
    elif result.decision == "review_required":
        segment.segment_status = "review_required"
        segment.review_flag = True
    else:
        segment.segment_status = "normalized"
        segment.review_flag = False

    segment.issues_json = merged_issues
    segment.save(
        update_fields=[
            "normalized_text",
            "final_text",
            "semantic_score",
            "semantic_payload",
            "llm_provider",
            "segment_status",
            "review_flag",
            "issues_json",
            "updated_at",
        ]
    )
    return segment
