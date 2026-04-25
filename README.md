# RAG-QA-pipeline-GCP

Hybrid RAG 기반 학생/청년 정부 정책 QnA 시스템. 멀티 LLM 응답 신뢰성을 3단계 자동 평가로 비교하는 파이프라인.

> **구현 현황** (2026-04-22): 수집/검색/생성 파이프라인 완료 (151 tests passed). 정책 2,235건 수집, QA 100쌍 생성, FAISS 인덱스 빌드 완료. 평가/UI/API 라우트는 미구현.

---

## 주요 기능

- **Hybrid 검색**: Vector (FAISS) + BM25 + Cross-Encoder Reranker (RRF k=60)
- **멀티 LLM 비교**: GPT-4o, Claude Sonnet, Gemini Flash, Llama 3.2 — LiteLLM으로 1줄 전환
- **3단계 신뢰성 평가**: RAGAS v0.4 정량 / LLM Judge 정성 / DeepEval 안전성 자동화
- **정책 도메인 특화**: 온통청년, 공공데이터포털, 한국장학재단, 정부 PDF 보고서 수집
- **QA 데이터셋 자동 생성**: 정책 원본 → GPT-4o-mini로 100쌍 자동 생성 (`scripts/generate_qa.py`)
- **GCP 배포**: Cloud Run scale-to-zero (BE FastAPI 2Gi / FE Streamlit 512Mi)
- **CI/CD**: GitHub Actions 4개 워크플로 (lint+test, BE/FE/Jobs 자동 배포)
- **제품 수준 UI** (예정): Streamlit 6페이지 (정책 탐색 / QnA 챗봇 / 정책 비교 / 맞춤 추천 / 평가 대시보드 / 소개)

---

## 아키텍처

![RAG-QA Pipeline Architecture](docs/rag-qa-pipeline(1).drawio.png)

> 📎 [draw.io 원본 파일](docs/rag-qa-pipeline.drawio) — 다이어그램 편집 가능

**데이터 흐름**

1. 수집: 정부사이트 → collectors → GCS (원본 JSON/PDF) + MongoDB (메타데이터: policy_id, title, gcs_path, status)
2. 인덱싱: GCS 원본 → chunker → embedder → FAISS index + metadata.pkl → GCS 업로드
3. 서빙: Cloud Run 기동 시 GCS에서 FAISS 인덱스 다운로드 → 인메모리 검색
4. 오케스트레이션: Airflow DAGs — 수집+인덱싱 (매일 02:00 KST), 평가/QA 생성 (수동 트리거)
5. QA 생성: 정책 원본 → GPT-4o-mini 자동 생성 → `data/eval/qa_pairs.json` (100쌍 완료)
6. 평가 (예정): QA 데이터셋 × 모델 × 전략 → 3단계 평가 → JSON 리포트

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| LLM 통합 | LiteLLM (GPT-4o, Claude Sonnet, Gemini Flash, Llama 3.2) |
| 임베딩 | OpenAI text-embedding-3-small |
| 벡터 검색 | FAISS (faiss-cpu) + pickle 직렬화 |
| 키워드 검색 | rank-bm25 |
| 리랭킹 | sentence-transformers Cross-Encoder |
| 평가 (정량) | RAGAS v0.4 (Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall) |
| 평가 (정성) | 커스텀 LLM Judge (G-Eval 방식) |
| 평가 (안전성) | DeepEval HallucinationMetric |
| 데이터 수집 | httpx + BeautifulSoup4, PyMuPDF |
| 한국어 처리 | kss (문장 분리), tiktoken |
| 백엔드 | FastAPI + uvicorn |
| 프론트엔드 | Streamlit |
| 데이터 저장 | GCS (정책 원본 + FAISS 인덱스), MongoDB (메타데이터) |
| 워크플로 오케스트레이션 | Apache Airflow 2.9.3 (self-hosted VM) |
| 배포 | GCP Cloud Run, Artifact Registry |
| 모니터링 | Grafana + GCP Cloud Monitoring + Cloud Logging |
| CI/CD | GitHub Actions (경로 필터 기반 자동 배포) |
| 린터/포매터 | ruff |
| 테스트 | pytest |

---

## 프로젝트 구조

```
src/
├── api/                  # FastAPI 백엔드 (Cloud Run #1)
│   ├── main.py           # 앱 엔트리 (헬스체크만 — 라우트 미구현)
│   └── routes/           # (예정) /search, /generate, /policies, /evaluate
├── ingestion/            # ✅ 수집 → GCS + MongoDB → FAISS 인덱스 빌드
│   ├── gcs_client.py     # GCS 업로드/다운로드 클라이언트
│   ├── collectors/       # data_portal (✅), youthgo/kosaf/pdf (예정)
│   ├── chunker.py        # 정책 구조 인식 청킹 (kss + tiktoken)
│   ├── loader.py         # PDF/TXT/JSON 로더
│   ├── embedder.py       # OpenAI 임베딩 래퍼
│   ├── mongo_client.py   # MongoDB 메타데이터 CRUD
│   └── pipeline.py       # 수집 통합 CLI
├── retrieval/            # ✅ 4가지 검색 전략
│   ├── vector_store.py   # FAISS 래퍼
│   ├── bm25_store.py     # BM25 키워드 검색
│   ├── hybrid.py         # RRF (k=60)
│   ├── reranker.py       # Cross-Encoder
│   └── pipeline.py       # 검색 통합 CLI
├── generation/           # ✅ LiteLLM 래퍼 + 정책 도메인 프롬프트 + RAG 오케스트레이션
│   ├── llm_client.py     # LiteLLM 통합 클라이언트
│   ├── prompt.py         # 한국어 정책 도메인 프롬프트
│   └── pipeline.py       # RAG 파이프라인 CLI
├── evaluation/           # (예정) 3단계 평가 통합
└── ui/                   # (예정) Streamlit 6페이지 (Cloud Run #2)

config/                   # ✅ pydantic-settings, 모델 목록, 데이터 소스 설정
data/
├── policies/raw/         # 수집 데이터 (data_portal 2,185건 + youthgo 50건)
├── index/                # FAISS 인덱스 (faiss.index 16.5MB + metadata.pkl 3MB)
├── eval/qa_pairs.json    # ✅ 평가 QA 데이터셋 (100쌍 생성 완료)
└── results/              # 평가 결과 JSON
scripts/
├── collect_policies.py   # 정책 데이터 일괄 수집
├── generate_qa.py        # QA 데이터셋 자동 생성 (GPT-4o-mini)
├── collect_youthgo_sample.py
├── verify_data_portal_api.py
└── verify_ragas_v04.py
tests/                    # 151 tests passed
```

---

## 시작하기

### 요구사항

- Python 3.11+
- GCP 계정 (Cloud Run, GCS, Compute Engine 사용)
- MongoDB (GCP VM 또는 로컬)

### 설치

```bash
git clone https://github.com/Daehyun-Bigbread/RAG-QA-pipeline-GCP.git
cd RAG-QA-pipeline-GCP

pip install -e ".[dev,ui,ko,crawl,viz]"
```

### 환경변수

`.env.example`을 복사하여 `.env`를 생성하고 각 값을 채운다.

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DATA_PORTAL_API_KEY=        # 공공데이터포털 API 키
MONGODB_URI=mongodb://MONGO_VM_IP:27017
MONGODB_DB=rag_youth_policy
GCP_PROJECT=rag-qna-eval
GCS_BUCKET=rag-qna-eval-data
API_BASE_URL=               # FE -> BE 통신 URL (Cloud Run 배포 시 설정)
```

### 실행

```bash
# 1. 정책 수집 (GCS 원본 저장 + MongoDB 메타데이터)
python scripts/collect_policies.py --all

# 2. GCS 원본 -> FAISS 인덱스 빌드
python -m src.ingestion.pipeline --output data/index/

# 3. GCS에 인덱스 업로드
gsutil cp data/index/* gs://rag-qna-eval-data/index/

# 4. 검색 테스트
python -m src.retrieval.pipeline --query "청년 월세 지원 신청 자격은?" --strategy hybrid_rerank

# 5. 답변 생성 테스트
python -m src.generation.pipeline \
  --query "청년 월세 지원 신청 자격은?" \
  --model openai/gpt-4o-mini \
  --strategy hybrid_rerank

# 6. UI 실행
streamlit run src/ui/app.py
```

### 테스트 및 린트

```bash
pytest                           # 전체 테스트 (151 passed)
pytest tests/test_ingestion.py   # 단일 모듈
pytest --cov=src --cov-report=term-missing  # 커버리지
ruff check .
ruff format .
```

---

## 검색 전략

| 전략 | 파이프라인 |
|------|----------|
| `vector_only` | FAISS 벡터 검색 -> Top-K |
| `bm25_only` | BM25 키워드 검색 -> Top-K |
| `hybrid` | Vector + BM25 -> RRF (k=60) -> Top-K |
| `hybrid_rerank` | Vector + BM25 -> RRF -> Cross-Encoder -> Top-K |

---

## 평가 파이프라인 (3단계) — 예정

> 아래는 설계 완료된 평가 체계이다. `src/evaluation/`은 아직 미구현 (스텁만 존재).

이 프로젝트의 핵심 차별화 포인트는 RAG 응답을 3가지 관점에서 자동 평가하는 것이다.

### Stage 1: RAGAS v0.4 — 정량 평가

검색 품질과 생성 품질을 수치로 측정한다.

| 메트릭 | 측정 대상 | 목표 |
|--------|----------|------|
| Faithfulness | 답변이 컨텍스트에 근거하는가 (claim 분해 후 NLI) | >= 0.85 |
| AnswerRelevancy | 답변이 질문과 관련 있는가 (역질문 유사도) | >= 0.80 |
| ContextPrecision | 검색 문서가 정답 생성에 기여하는가 (AP) | >= 0.75 |
| ContextRecall | 정답의 근거가 컨텍스트에 있는가 | >= 0.80 |

`ragas>=0.4,<0.5` 버전 고정 필수. `evaluate()` 대신 `metric.ascore()` 사용.

### Stage 2: LLM-as-a-Judge — 정성 평가

G-Eval 방식으로 3가지 항목을 1-5점으로 평가한다.

| 평가 항목 | 기준 |
|----------|------|
| 인용 정확성 | 답변 인용이 컨텍스트와 일치하는가 |
| 답변 완결성 | 질문에 빠짐없이 답했는가 |
| 가독성 | 읽기 쉽고 구조적인가 |

Position Bias 완화를 위해 순서를 바꿔 2회 평가한 후 평균한다. 생성 모델과 Judge 모델은 다른 모델을 사용한다.

### Stage 3: DeepEval — 안전성 평가 (Hallucination)

RAGAS Faithfulness와 구분되는 보완적 관점이다.

```
RAGAS Faithfulness:     "증거 없음" = 불충실
DeepEval Hallucination: "명시적 모순" = hallucination
```

두 메트릭을 함께 사용해야 응답 오류의 성격을 정확히 진단할 수 있다.

### 실험 매트릭스

```
실험 1: 모델 비교 (검색 전략 고정: hybrid_rerank)
  GPT-4o / GPT-4o-mini / Claude Sonnet / Gemini Flash / Llama 3.2

실험 2: 검색 전략 비교 (모델 고정: GPT-4o-mini)
  vector_only / bm25_only / hybrid / hybrid_rerank

실험 3: RAG vs No-RAG (모델 고정: GPT-4o-mini)
  컨텍스트 있음 vs 없음
```

---

## 배포 (GCP Cloud Run)

BE(FastAPI)와 FE(Streamlit)를 별도 Cloud Run 서비스로 분리 배포한다.

```bash
# BE (FastAPI, 2Gi) 이미지 빌드 및 배포
docker build -t rag-youth-policy-api .
gcloud run deploy rag-youth-policy-api \
  --image ... \
  --region asia-northeast3 \
  --memory 2Gi \
  --min-instances 0 \
  --max-instances 1

# FE (Streamlit, 512Mi) 이미지 빌드 및 배포
docker build -t rag-youth-policy-ui -f Dockerfile.ui .
gcloud run deploy rag-youth-policy-ui \
  --image ... \
  --region asia-northeast3 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 1
```

| 서비스 | 메모리 | 이유 |
|--------|--------|------|
| BE (FastAPI) | 2Gi | Cross-Encoder 모델 로드 |
| FE (Streamlit) | 512Mi | UI 전용, 경량 |

Cold start는 5~15초이므로 발표 전 사전 호출을 권장한다.

### CI/CD

GitHub Actions 4개 워크플로로 모노레포 경로 필터를 적용해 변경된 서비스만 배포한다.

| 워크플로 | 트리거 | 동작 |
|----------|--------|------|
| `ci.yml` | PR -> main | ruff lint + pytest |
| `deploy-api.yml` | main push (`src/api`, `src/retrieval` 등 변경 시) | BE 빌드 + 배포 |
| `deploy-ui.yml` | main push (`src/ui` 변경 시) | FE 빌드 + 배포 |
| `deploy-jobs.yml` | main push (`src/ingestion`, `scripts/` 변경 시) | Collector/Indexer Job 빌드 + 배포 |

GitHub Secrets에 `GCP_SA_KEY` (서비스 계정 JSON 키) 설정이 필요하다.

### 인프라 구성

| 구성 요소 | 사양 | 역할 |
|----------|------|------|
| Cloud Run #1 (BE) | 2Gi, max 1 instance | FastAPI + FAISS 인메모리 검색 |
| Cloud Run #2 (FE) | 512Mi, max 1 instance | Streamlit UI |
| Compute Engine VM #1 | e2-small, 서울 | MongoDB + Grafana (메타데이터 + 모니터링) |
| Compute Engine VM #2 | e2-standard-2, 서울 | Airflow 2.9.3 (DAG 오케스트레이션) |
| Cloud Storage | — | 정책 원본 JSON/PDF + FAISS 인덱스 |
| Cloud Monitoring | — | Cloud Run 메트릭 + FastAPI 커스텀 메트릭 |
| Cloud Logging | — | RAG 요청별 구조화 JSON 로그 |

---

## 데이터 소스

| 소스 | 데이터 유형 | 수집 방법 | 상태 |
|------|------------|---------|------|
| 공공데이터포털 (data.go.kr) | 청년정책 구조화 JSON | REST API | ✅ 2,185건 |
| 온통청년 (youth.go.kr) | 청년 정책 목록 + 상세 | httpx + BeautifulSoup | ✅ 50건 (샘플) |
| 한국장학재단 (kosaf.go.kr) | 장학금/학자금 정보 | httpx + BeautifulSoup | 예정 |
| 정부 PDF 보고서 | 고용/주거 정책 | PyMuPDF | 예정 |

크롤링 규칙: robots.txt 준수, 요청 간격 2~3초, User-Agent 설정.

---

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE).
