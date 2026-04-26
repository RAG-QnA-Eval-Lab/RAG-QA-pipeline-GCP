"""BE API 클라이언트 — httpx 기반."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10.0
_LLM_TIMEOUT = 60.0


class APIClient:
    """FastAPI 백엔드 호출을 래핑하는 HTTP 클라이언트."""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=_DEFAULT_TIMEOUT,
        )

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            logger.exception("GET %s failed", path)
            return None

    def _post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict[str, Any] | None:
        try:
            resp = self._client.post(path, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            logger.exception("POST %s failed", path)
            return None

    # ── Health ───────────────────────────────────────

    def health(self) -> dict[str, Any] | None:
        return self._get("/health")

    # ── Models ───────────────────────────────────────

    def get_models(self) -> dict[str, Any] | None:
        return self._get("/api/v1/models")

    # ── Search ───────────────────────────────────────

    def search(
        self,
        query: str,
        strategy: str = "hybrid_rerank",
        top_k: int = 5,
    ) -> dict[str, Any] | None:
        return self._post(
            "/api/v1/search",
            json={"query": query, "strategy": strategy, "top_k": top_k},
        )

    # ── Generate ─────────────────────────────────────

    def generate(
        self,
        query: str,
        *,
        model: str | None = None,
        strategy: str = "hybrid_rerank",
        top_k: int = 5,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        no_rag: bool = False,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {
            "query": query,
            "strategy": strategy,
            "top_k": top_k,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "no_rag": no_rag,
        }
        if model:
            payload["model"] = model
        return self._post("/api/v1/generate", json=payload, timeout=_LLM_TIMEOUT)

    # ── Policies ─────────────────────────────────────

    def get_policies(
        self,
        category: str | None = None,
        page: int = 1,
        limit: int = 12,
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {"page": page, "limit": limit}
        if category:
            params["category"] = category
        return self._get("/api/v1/policies", params=params)

    def get_policy(self, policy_id: str) -> dict[str, Any] | None:
        return self._get(f"/api/v1/policies/{policy_id}")

    # ── Evaluate ─────────────────────────────────────

    def evaluate(
        self,
        samples: list[dict[str, Any]],
        judge_model: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"samples": samples}
        if judge_model:
            payload["judge_model"] = judge_model
        return self._post("/api/v1/evaluate", json=payload, timeout=_LLM_TIMEOUT)


@st.cache_resource
def get_api_client() -> APIClient:
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")
    return APIClient(base_url=base_url, api_key=api_key)
