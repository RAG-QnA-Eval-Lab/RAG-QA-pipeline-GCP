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
  Cloud Scheduler           — 배치 수집 트리거 (매일 1회)

src/
├── api/                # FastAPI 백엔드 (Cloud Run #1, 2Gi) — /search, /generate, /policies, /evaluate
├── ingestion/          # 수집 → GCS 원본 저장 + MongoDB 메타데이터 → 청킹 → FAISS 인덱스 빌드
│   ├── collectors/     # 정부 사이트별 크롤러 (온통청년, 공공데이터포털, 장학재단, PDF)
│   └── mongo_client.py # MongoDB 메타데이터 CRUD + GCS 연동
├── retrieval/          # 4가지 검색 전략: vector_only, bm25_only, hybrid (RRF), hybrid_rerank
├── generation/         # LiteLLM 래퍼 + 정책 도메인 프롬프트 + RAG 오케스트레이션
├── evaluation/         # 3단계: RAGAS v0.4 정량 → LLM Judge 정성 → DeepEval 안전성
└── ui/                 # Streamlit 프론트엔드 (Cloud Run #2, 512Mi) — httpx로 BE API 호출
config/                 # pydantic-settings (Settings), 모델 목록, 데이터 소스 설정
data/
├── index/              # FAISS 인덱스 (faiss.index + metadata.pkl)
├── eval/qa_pairs.json  # 평가 QA 데이터셋 (50~100쌍)
└── results/            # 평가 결과 JSON
```

**MongoDB 컬렉션**:
- `policies`: 정책 메타데이터 (policy_id, title, category, gcs_path, status)
- `ingestion_logs`: 수집 이력 (소스, 건수, 인덱스 동기화 정보)
- `api_usage_logs`: LLM API 호출 이력 (모델, 토큰, 비용, 레이턴시)

**데이터 흐름**:
- 수집: 정부사이트 → collectors → GCS (원본 저장) + MongoDB (메타데이터: policy_id, title, gcs_path, status)
- QA 생성: 정책 원본 → LLM (GPT-4o-mini) 자동 생성 → 수동 검수 → data/eval/qa_pairs.json
- 인덱싱: GCS 원본 → chunker → embedder → FAISS index + metadata.pkl → GCS 업로드
- 서빙: Cloud Run 기동 → GCS에서 FAISS 인덱스 다운로드 → 인메모리 검색
- 지속 수집: Cloud Scheduler → Cloud Run Job → 수집기 → GCS + MongoDB → 인덱스 재빌드 → GCS
- 모니터링: FastAPI 커스텀 메트릭 → Cloud Monitoring → Grafana 대시보드

## Commands

```bash
# Setup
pip install -e ".[dev,ui,ko,crawl,viz]"

# Tests
pytest                              # 전체
pytest tests/test_ingestion.py      # 단일 모듈
pytest -k "test_chunk_size"         # 단일 테스트

# Lint
ruff check .
ruff format .

# Pipelines
python scripts/collect_policies.py --all                    # 정책 수집 → GCS + MongoDB 메타데이터
python -m src.ingestion.pipeline --output data/index/       # GCS 원본 → FAISS 인덱스 빌드
gsutil cp data/index/* gs://rag-qna-eval-data/index/         # GCS 업로드
python -m src.retrieval.pipeline --query "질문" --strategy hybrid_rerank   # 검색 테스트
python -m src.generation.pipeline --query "질문" --model openai/gpt-4o-mini --strategy hybrid_rerank

# UI
streamlit run src/ui/app.py

# Docker / GCP Deploy (BE + FE 분리)
docker build -t rag-youth-policy-api .                    # BE (FastAPI, 2Gi)
docker build -t rag-youth-policy-ui -f Dockerfile.ui .    # FE (Streamlit, 512Mi)
gcloud run deploy rag-youth-policy-api --image ... --memory 2Gi
gcloud run deploy rag-youth-policy-ui --image ... --memory 512Mi
```

## Key Technical Decisions

- **RAGAS v0.4 only** (not v0.3). 온라인 예시 대부분 v0.3이므로 주의. `ragas>=0.4,<0.5` pinning 필수. `evaluate()` 대신 `metric.ascore()` 사용.
- **LiteLLM** 으로 모델 전환: `openai/gpt-4o-mini`, `anthropic/claude-sonnet-4-20250514`, `gemini/gemini-2.0-flash`, `ollama/llama3.2`
- **FAISS (faiss-cpu)** 벡터 검색 + metadata dict (pickle). ChromaDB 대신 선택 — 경량, Cloud Run stateless 문제 없음.
- **GCS** 실제 데이터 저장소 (정책 원본 JSON/PDF + FAISS 인덱스). Cloud Run 기동 시 인덱스 다운로드.
- **MongoDB (GCP VM)** 메타데이터 전용 (정책 목록, 수집 이력, gcs_path 참조). Compass GUI로 모니터링.
- **Hybrid Search**: Vector + BM25 → RRF (k=60) → Cross-Encoder rerank
- **한국어 처리**: kss (문장 분리), tiktoken (토큰 카운트), 공백 기반 BM25 (시간 여유 시 konlpy/mecab)
- **Policy 스키마**: `collectors/base.py`의 frozen dataclass. 모든 수집기가 이 스키마로 정규화
- **크롤링 규칙**: robots.txt 준수, 요청 간격 2~3초, User-Agent 설정
- **OpenAI API mock**: 테스트에서 비용 절약 위해 mock 처리
- **모니터링**: Grafana + GCP Cloud Monitoring (Prometheus 없이 관리형 서비스 활용). VM에 Grafana만 추가 설치.
- **CI/CD**: GitHub Actions 3개 워크플로 — ci.yml (PR lint+test), deploy-api.yml (BE 자동배포), deploy-ui.yml (FE 자동배포). 모노레포 경로 필터.
- **헬스체크**: FastAPI `/health` — FAISS 로드 상태, MongoDB 연결, GCS 접근성, 데이터 파이프라인 상태 확인

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
- MongoDB VM: e2-small (~₩25,000/월), MongoDB + Grafana 동시 운영, GCP 크레딧으로 커버.
