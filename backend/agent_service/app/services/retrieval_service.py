from typing import Any


class RetrievalService:
    def search(self, query: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """
        TODO:
        - Integrate with RAGFlow multi-dataset retrieval
        - Normalize documents into the project document schema
        """
        return []
