from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI

from app.models.schemas import KnowledgeChunk

logger = logging.getLogger(__name__)


class KnowledgeSearchError(RuntimeError):
    pass


class KnowledgeService:
    def __init__(
        self,
        supabase_client: Any,
        openai_client: AsyncOpenAI,
        embedding_model: str,
        threshold: float = 0.72,
        match_count: int = 6,
    ) -> None:
        self.supabase = supabase_client
        self.openai = openai_client
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.match_count = match_count

    async def _embedding(self, text: str) -> list[float]:
        response = await self.openai.embeddings.create(model=self.embedding_model, input=text[:6000])
        return response.data[0].embedding

    async def search(self, query: str) -> list[KnowledgeChunk]:
        try:
            vector = await self._embedding(query)
            result = await asyncio.to_thread(
                self.supabase.rpc("match_knowledge_documents", {
                    "query_embedding": vector,
                    "match_threshold": self.threshold,
                    "match_count": self.match_count,
                }).execute
            )
            return [
                KnowledgeChunk(
                    content=row["content"],
                    source_url=row["source_url"],
                    page_title=row.get("page_title") or "AVIDENTIKA",
                    similarity=float(row.get("similarity", 0)),
                )
                for row in (result.data or [])
                if float(row.get("similarity", 0)) >= self.threshold
            ]
        except Exception as vector_error:
            logger.warning("Vector search unavailable, using PostgreSQL full-text fallback: %s", type(vector_error).__name__)
            try:
                result = await asyncio.to_thread(
                    self.supabase.rpc("search_knowledge_documents", {
                        "search_query": query,
                        "result_limit": self.match_count,
                    }).execute
                )
                return [
                    KnowledgeChunk(
                        content=row["content"],
                        source_url=row["source_url"],
                        page_title=row.get("page_title") or "AVIDENTIKA",
                        similarity=float(row.get("rank", 0)),
                    )
                    for row in (result.data or [])
                ]
            except Exception as exc:
                logger.exception("Knowledge search failed")
                raise KnowledgeSearchError("Knowledge search failed") from exc
