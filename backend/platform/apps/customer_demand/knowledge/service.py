from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


SOURCE_LABELS = {
    "paper": "公开文献",
    "standard": "标准规范",
    "case": "案例资料",
    "solution": "解决方案资料",
}


def _split_dataset_ids(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _compact_text(text: str, limit: int = 180) -> str:
    cleaned = " ".join((text or "").split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def _dataset_mapping() -> dict[str, list[str]]:
    return {
        "paper": _split_dataset_ids(getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_DATASET_PAPERS", "")),
        "standard": _split_dataset_ids(getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_DATASET_STANDARDS", "")),
        "case": _split_dataset_ids(getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_DATASET_CASES", "")),
        "solution": _split_dataset_ids(getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_DATASET_SOLUTIONS", "")),
    }


def _requested_source_types(session) -> list[str]:
    scope = session.knowledge_scope or {}
    source_types = scope.get("source_types")
    if isinstance(source_types, list):
        normalized = [str(item).strip() for item in source_types if str(item).strip() in SOURCE_LABELS]
        if normalized:
            return normalized
    return ["paper", "standard", "case", "solution"]


def _build_query(session, accepted_records: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in [
        session.customer_name,
        session.session_title,
        session.topic,
        session.industry,
        session.region,
        session.remarks,
    ]:
        if item:
            parts.append(str(item).strip())

    for record in accepted_records[:6]:
        text = str(record.get("text") or "").strip()
        if text:
            parts.append(text[:180])

    return " ".join(parts).strip()


def _normalize_documents(source_type: str, payload: dict[str, Any], snippet_limit: int) -> list[dict[str, Any]]:
    data = payload.get("data", payload)
    chunks = data.get("chunks") or data.get("docs") or data.get("records") or []
    normalized: list[dict[str, Any]] = []
    for item in chunks:
        content = (
            item.get("content")
            or item.get("text")
            or item.get("chunk")
            or item.get("snippet")
            or ""
        )
        title = (
            item.get("document_name")
            or item.get("title")
            or item.get("doc_name")
            or item.get("document_keyword")
            or item.get("filename")
            or ""
        )
        metadata = dict(item.get("metadata") or {})
        if item.get("document_id"):
            metadata.setdefault("document_id", item.get("document_id"))
        if item.get("dataset_id"):
            metadata.setdefault("dataset_id", item.get("dataset_id"))
        if item.get("positions"):
            metadata.setdefault("positions", item.get("positions"))

        snippet = _compact_text(content, snippet_limit)
        if not title and not snippet:
            continue

        normalized.append(
            {
                "source_type": source_type,
                "source_label": SOURCE_LABELS.get(source_type, source_type),
                "title": title or "未命名资料",
                "snippet": snippet,
                "score": item.get("score") or item.get("similarity") or 0,
                "metadata": metadata,
            }
        )
    return normalized


def retrieve_customer_demand_knowledge(
    session,
    accepted_records: list[dict[str, Any]],
    *,
    enabled: bool,
    lightweight: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "query": "",
            "context_lines": [],
            "sources": [],
            "error": "",
        }

    base_url = getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_BASE_URL", "").strip()
    api_key = getattr(settings, "CUSTOMER_DEMAND_RAGFLOW_API_KEY", "").strip()
    dataset_mapping = _dataset_mapping()
    source_types = [item for item in _requested_source_types(session) if dataset_mapping.get(item)]
    if not base_url or not api_key or not source_types:
        return {
            "enabled": False,
            "query": "",
            "context_lines": [],
            "sources": [],
            "error": "knowledge_unconfigured",
        }

    query = _build_query(session, accepted_records)
    if not query:
        return {
            "enabled": True,
            "query": "",
            "context_lines": [],
            "sources": [],
            "error": "empty_query",
        }

    per_group_top_k = 2 if lightweight else 3
    page_size = 4 if lightweight else 6
    snippet_limit = 120 if lightweight else 220
    documents: list[dict[str, Any]] = []

    try:
        for source_type in source_types:
            dataset_ids = dataset_mapping[source_type]
            response = requests.post(
                f"{base_url.rstrip('/')}/api/v1/retrieval",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "question": query,
                    "dataset_ids": dataset_ids,
                    "page": 1,
                    "page_size": page_size,
                    "top_k": per_group_top_k,
                    "similarity_threshold": 0.2,
                    "vector_similarity_weight": 0.3,
                    "keyword": False,
                    "metadata": {},
                },
                timeout=30,
            )
            response.raise_for_status()
            documents.extend(
                _normalize_documents(source_type, response.json(), snippet_limit=snippet_limit)
            )
    except requests.RequestException as exc:
        return {
            "enabled": True,
            "query": query,
            "context_lines": [],
            "sources": [],
            "error": str(exc),
        }

    documents.sort(key=lambda item: item.get("score", 0), reverse=True)
    unique_documents: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for item in documents:
        key = (
            item.get("source_type", ""),
            item.get("title", ""),
            item.get("snippet", ""),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_documents.append(item)

    capped_documents = unique_documents[: (3 if lightweight else 6)]
    context_lines = [
        f"[{item['source_label']}] {item['title']}：{item['snippet']}"
        for item in capped_documents
    ]

    return {
        "enabled": True,
        "query": query,
        "context_lines": context_lines,
        "sources": capped_documents,
        "error": "",
    }
