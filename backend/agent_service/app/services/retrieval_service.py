from typing import Any

import httpx

from app.config import settings


class RetrievalService:
    def _require_config(self) -> None:
        if not settings.ragflow_api_key or settings.ragflow_api_key == "replace-me":
            raise RuntimeError("请先配置 RAGFLOW_API_KEY 环境变量，然后再调用 RAGFlow 检索。")

    @staticmethod
    def _split_dataset_ids(raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    def _dataset_mapping(self) -> dict[str, list[str]]:
        return {
            "paper": self._split_dataset_ids(settings.ragflow_dataset_papers),
            "standard": self._split_dataset_ids(settings.ragflow_dataset_standards),
            "case": self._split_dataset_ids(settings.ragflow_dataset_cases),
            "solution": self._split_dataset_ids(settings.ragflow_dataset_solutions),
        }

    def _normalize_documents(self, source_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data", payload)
        chunks = data.get("chunks") or data.get("docs") or data.get("records") or []
        normalized = []
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
            normalized.append(
                {
                    "source_type": source_type,
                    "title": title,
                    "snippet": content,
                    "score": item.get("score") or item.get("similarity") or 0,
                    "metadata": metadata,
                    "reference": item,
                }
            )
        return normalized

    def _search_dataset_group(
        self,
        *,
        source_type: str,
        dataset_ids: list[str],
        query: str,
        filters: dict[str, Any],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not dataset_ids:
            return []

        response = httpx.post(
            f"{settings.ragflow_base_url.rstrip('/')}/api/v1/retrieval",
            headers={
                "Authorization": f"Bearer {settings.ragflow_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "question": query,
                "dataset_ids": dataset_ids,
                "page": 1,
                "page_size": top_k,
                "top_k": top_k,
                "similarity_threshold": 0.2,
                "vector_similarity_weight": 0.3,
                "keyword": False,
                "metadata": filters,
            },
            timeout=30,
        )
        response.raise_for_status()
        return self._normalize_documents(source_type, response.json())

    def search(self, query: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        self._require_config()
        documents = []
        for source_type, dataset_ids in self._dataset_mapping().items():
            documents.extend(
                self._search_dataset_group(
                    source_type=source_type,
                    dataset_ids=dataset_ids,
                    query=query,
                    filters=filters,
                    top_k=6,
                )
            )
        return sorted(documents, key=lambda item: item.get("score", 0), reverse=True)
