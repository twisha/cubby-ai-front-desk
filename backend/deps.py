"""FastAPI dependency providers — pull the singletons off app.state so routers
stay thin and the seams are injected, not imported concretely."""
from __future__ import annotations

from fastapi import Request

from backend.core.retrieval.index import Retriever
from backend.core.store.repo import Store


def get_retriever(request: Request) -> Retriever:
    return request.app.state.retriever


def get_store(request: Request) -> Store:
    return request.app.state.store
