# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hybrid RAG 기반 학생/청년 정부 정책 QnA 시스템. 멀티 LLM (GPT-4o, Claude, Gemini, Llama3) 응답 신뢰성을 3단계 평가 (RAGAS v0.4 + LLM Judge + DeepEval)로 비교하는 파이프라인. GCP Cloud Run 배포 대상. 개인 프로젝트 (졸업논문 + PyCon Korea CFP).

## Architecture

```
GCP 인프라:
  Cloud Storage (GCS)       — 실제 데이터 저장소 (정책 원본 JSON/PDF + FAISS 인덱스)
  Compute Engine VM #1      — MongoDB (메타데이터 전용, 34.50.21.132:27017) + Grafana (:3000)
  Compute Engine VM #2      — Airflow 2.9.3 (http://34.47.107.145:8080)
  Cloud Run #1 (BE, 2Gi)    — FastAPI + FAISS 인메모리 검색
  Cloud Run #2 (FE, 512Mi)  — Streamlit (httpx → BE API 호출)

src/
├── api/                # FastAPI 백엔드 — 6개 엔드포인트 (Health, Search, Generate, Policies, Models, Evaluate)
│   ├── main.py         # lifespan: FAISS 인덱스 로드 + MongoDB 연결. app.state에 저장
│   ├── deps.py         # FastAPI Depends: get_rag_pipeline(), get_mongo()
│   ├── schemas.py      # Pydantic 요청/응답 모델
│   ├── errors.py       # 글로벌 예외 핸들러
│   ├── middleware.py    # 요청 로깅 미들웨어
│   └── routes/         # search, generate, policies, models, evaluate
├── ingestion/          # 수집 → GCS 원본 저장 + MongoDB 메타데이터 → 청킹 → FAISS 인덱스 빌드
│   ├── collectors/     # 정부 사이트별 크롤러. base.py에 Policy frozen dataclass + BaseCollector ABC
│   ├── chunker.py      # 문장 경계 기반 청킹 (kss 한국어 분리 → tiktoken 토큰 카운트)
│   ├── embedder.py     # LiteLLM embedding API 래퍼 (배치 + 재시도)
│   ├── gcs_client.py   # GCS 업로드/다운로드
│   ├── mongo_client.py # PolicyMetadataStore — MongoDB 메타데이터 CRUD
│   └── pipeline.py     # 오케스트레이션: 로컬/GCS 모드 인덱스 빌드
├── retrieval/          # 4가지 검색 전략: vector_only, bm25_only, hybrid (RRF k=60), hybrid_rerank
│   ├── pipeline.py     # RetrievalPipeline — SearchStrategy enum으로 전략별 분기
│   └── ...             # vector_store, bm25_store, hybrid, reranker
├── generation/         # LiteLLM 래퍼 + 정책 도메인 프롬프트 + RAG 오케스트레이션
│   ├── llm_client.py   # generate() — LiteLLM completion (재시도 + 토큰/레이턴시 추적)
│   ├── prompt.py       # build_rag_prompt(), build_no_rag_prompt()
│   └── pipeline.py     # RAGPipeline.run() / run_no_rag()
├── evaluation/         # 3단계 평가 구현 완료
│   ├── ragas_metrics.py    # evaluate_ragas() — RAGAS v0.4 SingleTurnSample 기반
│   ├── llm_judge.py        # judge_response() — G-Eval 방식, Position Bias 완화 (2회 평가 평균)
│   ├── safety_metrics.py   # evaluate_safety() — DeepEval HallucinationMetric
│   ├── evaluator.py        # RAGEvaluator — 3단계 통합 오케스트레이터
│   └── report.py           # generate_report() — JSON + HTML 리포트
└── ui/                 # Streamlit 프론트엔드 (미구현, 스텁만 존재)

config/
├── settings.py         # pydantic-settings Settings 클래스 (.env 자동 로드). 싱글톤: settings
├── models.py           # MODELS dict — 모델 키 → LiteLLM ID 매핑. resolve_model_key()로 조회
└── policy_sources.py   # POLICY_SOURCES dict — 데이터 소스별 URL/수집방식

dags/                   # Airflow DAGs (VM #2에 배포)
├── dag_collect_index.py    # 수집+인덱싱 (매일 02:00 KST)
├── dag_qa_generation.py    # QA 데이터셋 생성 (수동 트리거)
└── dag_evaluation.py       # 평가 실행 (수동 트리거)
```

**핵심 데이터 타입 (frozen dataclass)**:
- `Policy` (`src/ingestion/collectors/base.py`) — 정책 표준 스키마, 모든 수집기가 이 형태로 정규화
- `SearchResult` (`src/retrieval/__init__.py`) — 검색 결과 (content, score, metadata, rank)
- `LLMResponse`, `RAGResponse` (`src/generation/__init__.py`) — LLM 응답 + RAG 통합 응답
- `RagasResult`, `JudgeResult`, `SafetyResult`, `EvalResult` (`src/evaluation/__init__.py`) — 평가 결과

**데이터 흐름**:
1. 수집: 정부사이트 → collectors → GCS (원본 저장) + MongoDB (메타데이터)
2. 인덱싱: GCS/로컬 원본 → loader → chunker → embedder → FAISS index + metadata.pkl
3. 서빙: Cloud Run 기동 → GCS에서 FAISS 다운로드 → RetrievalPipeline → RAGPipeline → LLM 생성
4. 오케스트레이션: Airflow DAGs — 수집+인덱싱 매일 02:00, 평가/QA 생성 수동 트리거

**FastAPI API 라우트**:

| 엔드포인트 | 메서드 | 용도 |
|-----------|--------|------|
| `/health` | GET | FAISS/MongoDB 상태 + 업타임 |
| `/api/v1/search` | POST | 검색만 (SearchRequest → SearchResponse) |
| `/api/v1/generate` | POST | RAG 생성 (GenerateRequest → GenerateResponse). no_rag 옵션 |
| `/api/v1/policies` | GET | 정책 목록 (category/page/limit 쿼리 파라미터) |
| `/api/v1/policies/{id}` | GET | 정책 상세 |
| `/api/v1/models` | GET | 사용 가능 모델 + default_model |
| `/api/v1/evaluate` | POST | 3단계 평가 실행 (EvalRequest → EvalResponse) |

## Implementation Progress

`docs/plan.md`에 Phase 0~6 구현 계획이 정의되어 있다.

- Phase 0 (준비): 완료
- Phase 1 (수집+인덱싱): 완료. 정책 2,235건 수집, FAISS 인덱스 빌드
- Phase 2 (검색): 완료. 4가지 전략 + 코드리뷰 + 버그 수정
- Phase 3 (생성): 완료. LiteLLM + Vertex AI 통합
- Phase 4 (평가): 완료. RAGAS v0.4 + LLM Judge + DeepEval 3단계 구현
- FastAPI API: 완료. 6개 엔드포인트 + 미들웨어 + 에러 핸들링
- Phase 5 (UI): **미착수** — `src/ui/`는 스텁만 존재. 구현 계획은 `.claude/plans/` 참조
- Phase 6 (배포+실험): Dockerfile 4종 + GitHub Actions 4종 작성 완료
- QA 데이터셋: 100쌍 생성 완료 (`data/eval/qa_pairs.json`)
- 테스트: 210 passed (API 26 + 평가 + 수집/검색/생성)

## Commands

```bash
# Setup
pip install -e ".[dev,api,ingestion,indexer,ko,eval,monitoring,crawl,ui,viz]"

# Tests (210 tests)
pytest                              # 전체
pytest tests/test_api.py            # 단일 모듈
pytest -k "test_chunk_size"         # 패턴 매칭
pytest --cov=src --cov-report=term-missing

# Lint
ruff check .
ruff format .

# Pipelines
python scripts/collect_policies.py --all                                        # 정책 수집
python -m src.ingestion.pipeline --input data/policies/raw --output data/index  # 로컬 인덱스 빌드
python -m src.ingestion.pipeline --gcs --bucket rag-qna-eval-data              # GCS 모드 인덱스 빌드
python -m src.retrieval.pipeline --query "질문" --strategy hybrid_rerank       # 검색 테스트
python -m src.generation.pipeline --query "질문" --model gemini-flash --strategy hybrid_rerank

# BE (로컬)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# FE (로컬 — BE 서버 실행 필요)
streamlit run src/ui/app.py

# Docker
docker build -t rag-youth-policy-api .                    # BE
docker build -t rag-youth-policy-ui -f Dockerfile.ui .    # FE
```

## Key Technical Decisions

- **RAGAS v0.4 only** (not v0.3). `ragas>=0.4,<0.5` pinning 필수. `evaluate()` 대신 `metric.single_turn_ascore()` 사용. 온라인 예시 대부분 v0.3이므로 주의.
- **LiteLLM 멀티 프로바이더** 모델 통합. 모델 키를 `config/models.py`의 `MODELS` dict에서 LiteLLM ID로 매핑 (`resolve_model_key()`). 프로바이더별 경로: OpenAI 직접 호출 `openai/gpt-4o-mini`, Vertex AI Model Garden `vertex_ai/gemini-2.5-flash` · `vertex_ai/claude-sonnet-4-5`, HuggingFace `huggingface/meta-llama/Llama-3.3-70B-Instruct`.
- **FAISS (faiss-cpu)** + metadata dict (pickle). Cloud Run stateless에 적합. ChromaDB 대신 선택.
- **GCS** = 실제 데이터 저장소. **MongoDB** = 메타데이터 전용. Cloud Run 기동 시 GCS에서 FAISS 인덱스 다운로드.
- **Hybrid Search**: Vector + BM25 → RRF (k=60) → Cross-Encoder rerank. `SearchStrategy` enum으로 4가지 전략 제어.
- **한국어 처리**: kss (문장 분리, optional import), tiktoken cl100k_base (토큰 카운트), 공백 기반 BM25 토크나이징.
- **Policy 스키마**: `collectors/base.py`의 frozen dataclass. `REQUIRED_FIELDS` + `CATEGORY_MAP`/`VALID_CATEGORIES` 정규화.
- **테스트**: 외부 API (OpenAI, MongoDB, GCS) 모두 mock 처리. `tests/conftest.py`에 공유 fixtures.
- **CI/CD**: GitHub Actions 4종 — `ci.yml` (PR lint+test), `deploy-api.yml` (BE), `deploy-ui.yml` (FE), `deploy-jobs.yml` (수집/인덱싱 Job).
- **FastAPI lifespan**: `app.state.rag_pipeline` (RAGPipeline), `app.state.mongo` (PolicyMetadataStore). 라우트에서 `deps.py`의 `get_rag_pipeline()`, `get_mongo()`로 접근.
- **Airflow DAG 경로**: `_validate_path()`로 `ALLOWED_DATA_DIR = /opt/rag-pipeline/data` 내부로 제한. params의 경로는 `data/` 기준 상대경로.

## Environment Variables (.env)

로컬 개발은 `.env`, GCP 배포 런타임은 Secret Manager를 사용한다.

```
DATA_PORTAL_API_KEY=         # 공공데이터포털 API
MONGODB_URI=mongodb://34.50.21.132:27017
MONGODB_DB=rag_youth_policy
GCP_PROJECT=rag-qna-eval
GCS_BUCKET=rag-qna-eval-data
VERTEXAI_PROJECT=rag-qna-eval
VERTEXAI_LOCATION=asia-northeast3
API_BASE_URL=                # FE → BE 통신 URL (Cloud Run 배포 시 설정)
```

## Constraints

- GCP 크레딧 ₩786,544 (2026-06-19 만료, 일회성). Region: asia-northeast3 (서울).
- 모든 코드와 UI는 한국어 도메인 (정부 정책).
- Cloud Run: scale-to-zero, max 1 instance, 2Gi memory (Cross-Encoder 로드).
- ruff: line-length 120, target Python 3.11+. lint rules: E, F, W, I.
- Dockerfile CMD: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` (Cloud Run은 `PORT` 환경변수 주입).
- 크롤링: robots.txt 준수, 요청 간격 2~3초, User-Agent 설정.
