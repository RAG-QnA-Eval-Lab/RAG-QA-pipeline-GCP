"""FastAPI 엔드포인트 테스트 — 파이프라인 mock 처리."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import _APP_VERSION, _redact_mongo_target
from src.generation import LLMResponse, RAGResponse
from src.retrieval import SearchResult

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture()
def mock_rag_pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.retrieval = MagicMock()
    pipeline.retrieval.index = MagicMock()
    pipeline.retrieval.index.ntotal = 100
    return pipeline


@pytest.fixture()
def mock_mongo() -> MagicMock:
    mongo = MagicMock()
    mongo.client.admin.command.return_value = {"ok": 1}
    return mongo


@pytest.fixture()
def client(mock_rag_pipeline: MagicMock, mock_mongo: MagicMock) -> TestClient:
    from src.api.main import app

    app.state.rag_pipeline = mock_rag_pipeline
    app.state.mongo = mock_mongo
    app.state.boot_time = 0.0
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def sample_search_results() -> list[SearchResult]:
    return [
        SearchResult(
            content="청년 월세 지원 정책입니다.",
            score=0.95,
            metadata={"title": "월세 지원", "category": "housing", "policy_id": "P001"},
            rank=1,
        ),
        SearchResult(
            content="취업 지원 정책입니다.",
            score=0.88,
            metadata={"title": "취업 지원", "category": "employment", "policy_id": "P002"},
            rank=2,
        ),
    ]


@pytest.fixture()
def sample_rag_response() -> RAGResponse:
    return RAGResponse(
        answer="청년 월세 지원은 매달 최대 20만원을 지원합니다.",
        sources=[
            {
                "content": "청년 월세 지원",
                "title": "월세 지원",
                "category": "housing",
                "source_name": "data_portal",
                "score": 0.95,
                "rank": 1,
            },
        ],
        model="vertex_ai/openai/gpt-4o-mini",
        search_strategy="hybrid_rerank",
        llm_response=LLMResponse(
            content="청년 월세 지원은 매달 최대 20만원을 지원합니다.",
            model="vertex_ai/openai/gpt-4o-mini",
            prompt_tokens=500,
            completion_tokens=100,
            total_tokens=600,
            latency=1.2,
        ),
        retrieval_latency=0.3,
        generation_latency=1.2,
    )


# ── Health ────────────────────────────────────────────────────


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["faiss_loaded"] is True
        assert data["faiss_doc_count"] == 100
        assert data["version"] == _APP_VERSION

    def test_health_mongo_down(self, client: TestClient, mock_mongo: MagicMock) -> None:
        mock_mongo.client.admin.command.side_effect = Exception("connection refused")
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["mongodb_connected"] is False

    def test_health_degraded_no_faiss(self, client: TestClient) -> None:
        client.app.state.rag_pipeline = None  # type: ignore[union-attr]
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["faiss_loaded"] is False
        assert data["faiss_doc_count"] == 0


# ── Search ────────────────────────────────────────────────────


class TestSearch:
    def test_search_success(
        self,
        client: TestClient,
        mock_rag_pipeline: MagicMock,
        sample_search_results: list[SearchResult],
    ) -> None:
        mock_rag_pipeline.retrieval.search.return_value = sample_search_results
        resp = client.post(
            "/api/v1/search",
            json={"query": "청년 주거 지원", "strategy": "hybrid_rerank", "top_k": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["strategy"] == "hybrid_rerank"
        assert len(data["results"]) == 2
        assert data["results"][0]["rank"] == 1

    def test_search_metadata_filtered(
        self,
        client: TestClient,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        mock_rag_pipeline.retrieval.search.return_value = [
            SearchResult(
                content="test",
                score=0.9,
                metadata={"title": "T", "category": "housing", "internal_path": "/gcs/secret"},
                rank=1,
            ),
        ]
        resp = client.post("/api/v1/search", json={"query": "test"})
        assert resp.status_code == 200
        meta = resp.json()["results"][0]["metadata"]
        assert "internal_path" not in meta
        assert meta["title"] == "T"

    def test_search_empty_query(self, client: TestClient) -> None:
        resp = client.post("/api/v1/search", json={"query": "", "strategy": "hybrid_rerank"})
        assert resp.status_code == 422

    def test_search_invalid_strategy(self, client: TestClient) -> None:
        resp = client.post("/api/v1/search", json={"query": "test", "strategy": "invalid"})
        assert resp.status_code == 422


# ── Generate ──────────────────────────────────────────────────


class TestGenerate:
    def test_generate_success(
        self,
        client: TestClient,
        mock_rag_pipeline: MagicMock,
        sample_rag_response: RAGResponse,
    ) -> None:
        mock_rag_pipeline.run.return_value = sample_rag_response
        resp = client.post("/api/v1/generate", json={"query": "청년 월세 지원 자격은?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert data["model"] == "vertex_ai/openai/gpt-4o-mini"
        assert data["strategy"] == "hybrid_rerank"
        assert data["token_usage"]["total_tokens"] == 600
        assert len(data["sources"]) == 1

    def test_generate_no_rag(
        self,
        client: TestClient,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        no_rag_resp = RAGResponse(
            answer="답변입니다.",
            sources=[],
            model="vertex_ai/openai/gpt-4o-mini",
            search_strategy="no_rag",
            llm_response=LLMResponse(
                content="답변입니다.",
                model="vertex_ai/openai/gpt-4o-mini",
                latency=0.5,
            ),
            retrieval_latency=0.0,
            generation_latency=0.5,
        )
        mock_rag_pipeline.run_no_rag.return_value = no_rag_resp
        resp = client.post("/api/v1/generate", json={"query": "청년 정책이란?", "no_rag": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy"] == "no_rag"
        assert data["sources"] == []
        mock_rag_pipeline.run_no_rag.assert_called_once()

    def test_generate_with_model_key(
        self,
        client: TestClient,
        mock_rag_pipeline: MagicMock,
        sample_rag_response: RAGResponse,
    ) -> None:
        mock_rag_pipeline.run.return_value = sample_rag_response
        resp = client.post("/api/v1/generate", json={"query": "test", "model": "gemini-flash"})
        assert resp.status_code == 200
        call_kwargs = mock_rag_pipeline.run.call_args
        assert call_kwargs.kwargs["model"] == "vertex_ai/gemini-2.5-flash"


# ── Policies ──────────────────────────────────────────────────


class TestPolicies:
    def test_list_policies(self, client: TestClient, mock_mongo: MagicMock) -> None:
        mock_mongo.list_all.return_value = [
            {"policy_id": "P001", "title": "월세 지원", "category": "housing"},
            {"policy_id": "P002", "title": "취업 지원", "category": "employment"},
        ]
        mock_mongo.count.return_value = 2
        resp = client.get("/api/v1/policies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["policies"]) == 2

    def test_list_policies_with_category(self, client: TestClient, mock_mongo: MagicMock) -> None:
        mock_mongo.find_by_category.return_value = [
            {"policy_id": "P001", "title": "월세 지원", "category": "housing"},
        ]
        mock_mongo.count.return_value = 1
        resp = client.get("/api/v1/policies?category=housing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        mock_mongo.find_by_category.assert_called_once()

    def test_list_policies_invalid_category(self, client: TestClient) -> None:
        resp = client.get("/api/v1/policies?category=invalid_cat")
        assert resp.status_code == 422

    def test_get_policy_found(self, client: TestClient, mock_mongo: MagicMock) -> None:
        mock_mongo.find_by_id.return_value = {
            "policy_id": "P001",
            "title": "월세 지원",
            "category": "housing",
        }
        resp = client.get("/api/v1/policies/P001")
        assert resp.status_code == 200
        assert resp.json()["policy_id"] == "P001"

    def test_get_policy_not_found(self, client: TestClient, mock_mongo: MagicMock) -> None:
        mock_mongo.find_by_id.return_value = None
        resp = client.get("/api/v1/policies/NONEXIST")
        assert resp.status_code == 404

    def test_policies_mongo_unavailable(self, client: TestClient) -> None:
        client.app.state.mongo = None  # type: ignore[union-attr]
        resp = client.get("/api/v1/policies")
        assert resp.status_code == 503


# ── Models ────────────────────────────────────────────────────


class TestModels:
    def test_list_models(self, client: TestClient) -> None:
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["models"]) >= 1
        keys = [m["key"] for m in data["models"]]
        assert "gemini-flash" in keys
        assert data["default_model"] is not None
        for m in data["models"]:
            assert "description" in m


# ── Evaluate ──────────────────────────────────────────────────


class TestEvaluate:
    @patch("src.api.routes.evaluate.RAGEvaluator")
    def test_evaluate_success(self, mock_evaluator_cls: MagicMock, client: TestClient) -> None:
        from src.evaluation import EvalResult, JudgeResult, RagasResult, SafetyResult

        mock_eval = mock_evaluator_cls.return_value
        mock_eval.evaluate_single.return_value = EvalResult(
            ragas=RagasResult(
                faithfulness=0.9,
                answer_relevancy=0.85,
                context_precision=0.8,
                context_recall=0.75,
            ),
            judge=JudgeResult(
                citation_accuracy=4.0,
                completeness=4.5,
                readability=4.0,
                average=4.17,
            ),
            safety=SafetyResult(hallucination_score=0.1),
            latency=2.5,
        )

        resp = client.post(
            "/api/v1/evaluate",
            json={
                "samples": [
                    {
                        "id": "q1",
                        "question": "청년 월세 지원?",
                        "answer": "답변",
                        "ground_truth": "정답",
                        "contexts": ["문맥1"],
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["evaluated"] == 1
        assert data["errors"] == 0
        assert data["results"][0]["ragas"]["faithfulness"] == 0.9

    @patch("src.api.routes.evaluate.RAGEvaluator")
    def test_evaluate_with_error(self, mock_evaluator_cls: MagicMock, client: TestClient) -> None:
        mock_eval = mock_evaluator_cls.return_value
        mock_eval.evaluate_single.side_effect = RuntimeError("LLM timeout")

        resp = client.post(
            "/api/v1/evaluate",
            json={
                "samples": [
                    {
                        "id": "q1",
                        "question": "test",
                        "answer": "a",
                        "ground_truth": "gt",
                        "contexts": ["c"],
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["errors"] == 1
        assert data["results"][0]["error"] == "evaluation_failed"

    def test_evaluate_invalid_sample_id(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/evaluate",
            json={
                "samples": [
                    {
                        "id": "invalid id!@#",
                        "question": "test",
                        "answer": "a",
                        "ground_truth": "gt",
                        "contexts": ["c"],
                    }
                ]
            },
        )
        assert resp.status_code == 422


# ── Error Handling ────────────────────────────────────────────


class TestErrorHandling:
    def test_unhandled_exception(self, client: TestClient, mock_rag_pipeline: MagicMock) -> None:
        mock_rag_pipeline.retrieval.search.side_effect = RuntimeError("unexpected")
        resp = client.post("/api/v1/search", json={"query": "test"})
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "internal_server_error"


# ── Middleware ────────────────────────────────────────────────


class TestMiddleware:
    def test_request_id_header(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) == 8


# ── Utility ──────────────────────────────────────────────────


class TestRedactMongoTarget:
    def test_empty_uri(self) -> None:
        assert _redact_mongo_target("") == "<unset>"

    def test_simple_uri(self) -> None:
        assert _redact_mongo_target("mongodb://10.0.0.5:27017/mydb") == "10.0.0.5/mydb"

    def test_uri_with_credentials(self) -> None:
        result = _redact_mongo_target("mongodb://admin:secret@10.0.0.5:27017/rag_db")
        assert result == "10.0.0.5/rag_db"
        assert "admin" not in result
        assert "secret" not in result

    def test_srv_uri(self) -> None:
        result = _redact_mongo_target("mongodb+srv://user:pass@cluster.mongodb.net/prod")
        assert result == "cluster.mongodb.net/prod"
        assert "pass" not in result
