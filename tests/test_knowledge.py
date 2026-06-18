import asyncio
from types import SimpleNamespace

from app.services.knowledge_service import KnowledgeService


class Embeddings:
    async def create(self, **kwargs):
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])


class OpenAI:
    embeddings = Embeddings()


class Builder:
    def __init__(self, data): self.data = data
    def execute(self): return SimpleNamespace(data=self.data)


class Supabase:
    def __init__(self, data): self.data = data; self.called = None
    def rpc(self, name, params): self.called = (name, params); return Builder(self.data)


def test_vector_search_returns_relevant_chunks() -> None:
    db = Supabase([{"content": "Ціна 1500 грн", "source_url": "https://avidentika.com.ua/x/", "page_title": "Ціни", "similarity": 0.91}])
    service = KnowledgeService(db, OpenAI(), "embed", threshold=0.72)
    result = asyncio.run(service.search("ціна"))
    assert result[0].content == "Ціна 1500 грн"
    assert db.called[0] == "match_knowledge_documents"


def test_search_returns_empty_when_no_match() -> None:
    service = KnowledgeService(Supabase([]), OpenAI(), "embed")
    assert asyncio.run(service.search("unknown")) == []
