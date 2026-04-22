# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hybrid RAG 기반 학생/청년 정부 정책 QnA 시스템. 멀티 LLM (GPT-4o, Claude, Gemini, Llama3) 응답 신뢰성을 3단계 평가 (RAGAS v0.4 + LLM Judge + DeepEval)로 비교하는 파이프라인. GCP Cloud Run 배포 대상. 개인 프로젝트 (졸업논문 + PyCon Korea CFP).

## Architecture

```
GCP 인프라:
  Cloud Storage (GCS)       — 실제 데이터 저장소 (정책 원본 JSON/PDF + FAISS 인덱스)
  Compute Engine (e2-small) — MongoDB (메타데이터 전용) + Grafana (:3000, 모니터링 대시보드)
  Cloud Run #1 (BE, 2Gi)    — FastAPI + FAISS 인메모리 검색
  Cloud Run #2 (FE, 512Mi)  — Streamlit (httpx → BE API 호출)
  Cloud Monitoring          — 메트릭 수집 (Cloud Run 기본 + FastAPI 커스텀)
  Cloud Logging             — 구조화 JSON 로그 (RAG 요청별 레이턴시/토큰/비용)
  Cloud Scheduler           — 수집 Job 트리거 (매일 1회)
  Eventarc                  — GCS 이벤트 → 인덱싱 Job 자동 체이닝

src/
├── api/                # FastAPI 백엔드 (Cloud Run #1, 2Gi) — /health (현재 스텁)
├── ingestion/          # 수집 → GCS 원본 저장 + MongoDB 메타데이터 → 청킹 → FAISS 인덱스 빌드
│   ├── collectors/     # 정부 사이트별 크롤러 (온통청년, 공공데이터포털, 장학재단, PDF)
│   │   └── base.py     # Policy frozen dataclass + BaseCollector ABC — 모든 수집기의 스키마/인터페이스
│   ├── chunker.py      # 문장 경계 기반 청킹 (kss 한국어 분리 → tiktoken 토큰 카운트)
│   ├── embedder.py     # LiteLLM embedding API 래퍼 (배치 + 재시도)
│   ├── loader.py       # JSON/PDF 파일 → Document dataclass
│   ├── gcs_client.py   # GCS 업로드/다운로드
│   ├── mongo_client.py # MongoDB 메타데이터 CRUD + GCS 연동
│   └── pipeline.py     # 오케스트레이션: 로컬/GCS 모드 인덱스 빌드
├── retrieval/          # 4가지 검색 전략: vector_only, bm25_only, hybrid (RRF), hybrid_rerank
│   ├── vector_store.py # FAISS IndexFlatL2 검색
│   ├── bm25_store.py   # rank-bm25 기반 키워드 검색
│   ├── hybrid.py       # RRF (k=60) 점수 융합
│   ├── reranker.py     # Cross-Encoder rerank
│   └── pipeline.py     # RetrievalPipeline — 전략별 분기 오케스트레이션
├── generation/         # LiteLLM 래퍼 + 정책 도메인 프롬프트 + RAG 오케스트레이션
│   ├── llm_client.py   # LiteLLM completion 래퍼 (재시도 + 토큰/레이턴시 추적)
│   ├── prompt.py       # RAG/No-RAG 프롬프트 빌더
│   └── pipeline.py     # RAGPipeline — 검색→프롬프트→생성 통합
├── evaluation/         # 3단계: RAGAS v0.4 정량 → LLM Judge 정성 → DeepEval 안전성 (미구현)
└── ui/                 # Streamlit 프론트엔드 (Cloud Run #2, 512Mi) — httpx로 BE API 호출 (미구현)
config/
├── settings.py         # pydantic-settings Settings 클래스 (.env 자동 로드)
├── models.py           # MODELS dict — LiteLLM 모델 ID + 파라미터
└── policy_sources.py   # POLICY_SOURCES dict — 데이터 소스별 URL/수집방식
```

**핵심 데이터 타입 (frozen dataclass)**:
- `Policy` (`src/ingestion/collectors/base.py`) — 정책 표준 스키마, 모든 수집기가 이 형태로 정규화
- `SearchResult` (`src/retrieval/__init__.py`) — 검색 결과 (content, score, metadata, rank)
- `LLMResponse`, `RAGResponse` (`src/generation/__init__.py`) — LLM 응답 + RAG 통합 응답

**데이터 흐름**:
- 수집: 정부사이트 → collectors → GCS (원본 저장) + MongoDB (메타데이터)
- 인덱싱: GCS/로컬 원본 → loader → chunker → embedder → FAISS index + metadata.pkl
- 서빙: Cloud Run 기동 → GCS에서 FAISS 인덱스 다운로드 → RetrievalPipeline (인메모리 검색) → RAGPipeline (LLM 생성)
- 지속 수집: Cloud Scheduler → 수집 Job → GCS + MongoDB → Eventarc → 인덱싱 Job → GCS

**MongoDB 컬렉션**: `policies` (메타데이터), `ingestion_logs` (수집 이력), `api_usage_logs` (LLM 호출 이력)

## Implementation Progress

`docs/plan.md`에 Phase 0~6 구현 계획이 정의되어 있다. 구현 시 해당 Phase 섹션을 반드시 참조할 것.

- Phase 0 (준비): 완료
- Phase 1 (수집+인덱싱): 코드 완료, GCS/MongoDB 실연결 미검증
- Phase 2 (검색): 코드 + 코드리뷰 + 버그 수정 완료
- Phase 3 (생성): 코드 완료, LLM 실호출 미검증 (mock 테스트만)
- Phase 4~6 (평가/UI/배포): **미착수** — `src/evaluation/`, `src/ui/`는 `__init__.py` 스텁만 존재
- QA 데이터셋: 100쌍 생성 완료 (`data/eval/qa_pairs.json`)
- GCP 배포: Dockerfile 4종 + GitHub Actions 4종 작성 완료, Secrets 등록/실배포 미완료

## Commands

```bash
# Setup
pip install -e ".[dev,api,ingestion,indexer,ko,eval,monitoring,crawl,ui,viz]"  # 전체 (로컬 개발)

# Tests
pytest                              # 전체 (151 tests)
pytest tests/test_ingestion.py      # 단일 모듈
pytest -k "test_chunk_size"         # 단일 테스트
pytest --cov=src --cov-report=term-missing  # 커버리지

# Lint
ruff check .
ruff format .

# RAGAS v0.4 API 검증 (LLM 호출 없이 import/구조만 확인)
python scripts/verify_ragas_v04.py

# Pipelines
python scripts/collect_policies.py --all                    # 정책 수집 → GCS + MongoDB
python -m src.ingestion.pipeline --input data/policies/raw --output data/index  # 로컬 인덱스 빌드
python -m src.ingestion.pipeline --gcs --bucket rag-qna-eval-data              # GCS 모드 인덱스 빌드
python -m src.retrieval.pipeline --query "질문" --strategy hybrid_rerank       # 검색 테스트
python -m src.generation.pipeline --query "질문" --model openai/gpt-4o-mini --strategy hybrid_rerank

# BE (로컬)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# UI (로컬)
streamlit run src/ui/app.py

# Docker
docker build -t rag-youth-policy-api .                    # BE (FastAPI)
docker build -t rag-youth-policy-ui -f Dockerfile.ui .    # FE (Streamlit)
```

## Key Technical Decisions

- **RAGAS v0.4 only** (not v0.3). 온라인 예시 대부분 v0.3이므로 주의. `ragas>=0.4,<0.5` pinning 필수. `evaluate()` 대신 `metric.ascore()` 사용.
- **LiteLLM** 으로 모델 전환. 모델 ID 형식: `openai/gpt-4o-mini`, `anthropic/claude-sonnet-4-20250514`, `gemini/gemini-2.0-flash`, `ollama/llama3.2`. 모델 정의는 `config/models.py`의 `MODELS` dict.
- **FAISS (faiss-cpu)** + metadata dict (pickle). ChromaDB 대신 선택 — 경량, Cloud Run stateless 문제 없음.
- **GCS** 실제 데이터 저장소. Cloud Run 기동 시 인덱스 다운로드. **MongoDB** 메타데이터 전용 (GCP VM).
- **Hybrid Search**: Vector + BM25 → RRF (k=60) → Cross-Encoder rerank. `SearchStrategy` enum으로 4가지 전략 제어.
- **한국어 처리**: kss (문장 분리, optional import), tiktoken cl100k_base (토큰 카운트), 공백 기반 BM25.
- **Policy 스키마**: `collectors/base.py`의 frozen dataclass. `REQUIRED_FIELDS` 검증 + `CATEGORY_MAP`/`VALID_CATEGORIES` 정규화.
- **크롤링 규칙**: robots.txt 준수, 요청 간격 2~3초, User-Agent 설정.
- **테스트**: OpenAI API mock 처리 (비용 절약). `tests/conftest.py`에 공유 fixtures (sample_policy, sample_api_response 등).
- **CI/CD**: GitHub Actions — `ci.yml` (PR lint+test), `deploy-api.yml` (BE), `deploy-ui.yml` (FE), `deploy-jobs.yml` (수집/인덱싱 Job).
- **설정**: `config/settings.py`의 `Settings` (pydantic-settings, `.env` 자동 로드). 임베딩 모델, 청크 크기, top_k 등 기본값 정의.

## Environment Variables (.env)

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DATA_PORTAL_API_KEY=     # 공공데이터포털 API
MONGODB_URI=mongodb://MONGO_VM_IP:27017
MONGODB_DB=rag_youth_policy
GCP_PROJECT=rag-qna-eval
GCS_BUCKET=rag-qna-eval-data
API_BASE_URL=                # FE → BE 통신 URL (Cloud Run 배포 시 설정)
GCP_SA_KEY=                  # GitHub Actions 시크릿 (서비스 계정 JSON 키)
```

## Constraints

- GCP 크레딧 ₩786,544 (2026-06-19 만료, 일회성). Region: asia-northeast3 (서울).
- 모든 코드와 UI는 한국어 도메인 (정부 정책).
- Cloud Run: scale-to-zero, max 1 instance, 2Gi memory (Cross-Encoder 로드).
- MongoDB VM: e2-small (~₩25,000/월), MongoDB + Grafana 동시 운영.
- ruff line-length: 120, target Python 3.11+.
- Dockerfile CMD: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` (Cloud Run은 `PORT` 환경변수 주입).
