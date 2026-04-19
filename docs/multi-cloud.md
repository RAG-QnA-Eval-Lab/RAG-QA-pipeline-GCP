# 멀티클라우드 아키텍처: GCP 데이터 파이프라인 + AWS 서빙

## 배경

이 프로젝트는 하나의 RAG QnA 시스템을 GCP와 AWS에 걸쳐 운영하는 통합 멀티클라우드 아키텍처다.

| 영역 | 인프라 | 담당 | 이유 |
|------|--------|------|------|
| **데이터 파이프라인** (수집/인덱싱) | GCP | 본인 단독 | 개인 프로젝트(졸업논문 + PyCon) — GCP 크레딧 ₩786,544 활용 |
| **서빙 + 평가** (API/UI/실험) | AWS | 캡스톤 팀 공용 | 팀원들이 AWS에 익숙, ECS Fargate로 공용 운영 |

**왜 나눴는가**: 데이터 파이프라인은 본인이 단독 설계/운영하므로 GCP 크레딧과 개인 프로젝트 인프라를 그대로 활용한다. 서빙 인프라는 캡스톤 팀원들과 함께 사용하며, 팀원들이 AWS에 익숙하므로 AWS ECS Fargate를 선택했다.

**파이프라인 이식성**: 수집 파이프라인의 핵심 로직(collectors)은 순수 Python 크롤링/API 호출 코드이므로 클라우드 종속성이 없다. 저장소 연결(GCS 업로드) 부분만 교체하면 다른 클라우드에서도 실행 가능하다.

---

## GCP 영역 (데이터 파이프라인)

GCP는 데이터 수집, 청킹, 인덱싱, 메타데이터 관리를 담당한다. Region: `asia-northeast3` (서울).

### 이벤트 드리븐 수집 흐름

```
Cloud Scheduler (매일 1회)
  → Cloud Run Job #1 (Data Crawler)
      → 정부 사이트 크롤링 (온통청년, 공공데이터포털, 한국장학재단, PDF)
      → GCS (원본 JSON/PDF 저장: gs://rag-qna-eval-data/policies/)
      + MongoDB VM (메타데이터 upsert: policy_id, title, gcs_path, status)
          → GCS 업로드 완료 이벤트
              → Eventarc (ObjectFinalize 트리거)
                  → Cloud Run Job #2 (Chunker & Embedder)
                      → 청킹 → 임베딩 → FAISS 인덱스 빌드
                      → GCS 업로드 (gs://rag-qna-eval-data/index/)
```

### GCP 서비스 구성

| 서비스 | 역할 | 상세 |
|--------|------|------|
| **Cloud Scheduler** | 수집 트리거 | 매일 1회 Cloud Run Job 호출 |
| **Cloud Run Job #1** | 데이터 수집기 | collectors → GCS 원본 저장 + MongoDB 메타데이터 |
| **Eventarc** | 이벤트 체이닝 | GCS ObjectFinalize → 인덱싱 Job 자동 트리거 |
| **Cloud Run Job #2** | 청킹/인덱싱 | GCS 원본 → chunker → embedder → FAISS → GCS |
| **Cloud Storage (GCS)** | 실제 데이터 저장소 | 정책 원본 JSON/PDF, FAISS 인덱스, 청크 데이터 |
| **Compute Engine** (e2-small) | MongoDB + Grafana | 메타데이터 관리 + 모니터링 대시보드 |
| **Cloud Logging** | 구조화 로그 | 수집/인덱싱 Job 실행 로그 |
| **Cloud Monitoring** | 메트릭 수집 | Cloud Run Job 실행 상태, GCS 용량 추이 |

### GCP CI/CD

GitHub Actions → Cloud Build → Artifact Registry → Cloud Run Job 배포. 수집/인덱싱 코드 변경 시 자동 빌드 및 배포.

---

## AWS 영역 (서빙 + 평가)

AWS는 사용자 대면 서빙(API + UI)과 RAG 평가 파이프라인을 담당한다.

### 서빙 아키텍처

```
Client (HTTPS)
  → ALB (Application Load Balancer)
      ├→ ECS Fargate: Front-End (Streamlit, 512Mi)
      │     └─ httpx → BE API 호출
      └→ ECS Fargate: Back-End (FastAPI + FAISS, 2Gi)
            ├─ /search    — 4가지 검색 전략 (vector_only, bm25_only, hybrid, hybrid_rerank)
            ├─ /generate  — RAG 답변 생성 (LiteLLM 경유 멀티 LLM)
            ├─ /policies  — 정책 메타데이터 조회
            ├─ /evaluate  — 3단계 평가 실행
            └─ /health    — 헬스체크 (FAISS 로드 상태, MongoDB 연결, GCS 접근성)
```

### AWS 서비스 구성

| 서비스 | 역할 | 상세 |
|--------|------|------|
| **ECR** | 컨테이너 레지스트리 | BE/FE Docker 이미지 저장 |
| **ECS Fargate (BE)** | 백엔드 API | FastAPI + FAISS 인메모리 검색, Memory 2Gi |
| **ECS Fargate (FE)** | 프론트엔드 | Streamlit 앱, Memory 512Mi |
| **ALB** | 로드밸런서 | HTTPS 종단, BE/FE 라우팅 |
| **CloudWatch** | 로그 + 메트릭 | ECS 로그, 요청 레이턴시, 에러율 |
| **Amazon Managed Grafana** | 모니터링 대시보드 | CloudWatch + MongoDB 데이터소스 연동 |

### 3단계 평가 파이프라인 (BE 내부)

| Stage | 도구 | 측정 대상 |
|-------|------|----------|
| **Stage 1**: 정량 평가 | RAGAS v0.4 | Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall |
| **Stage 2**: 정성 평가 | LLM-as-a-Judge | 인용 정확성, 답변 완결성, 가독성 (G-Eval 방식) |
| **Stage 3**: 안전성 평가 | DeepEval | HallucinationMetric (명시적 모순 검출) |

### AWS CI/CD

GitHub Actions → ECR Build & Push → ECS Fargate 배포. BE/FE 경로 필터 기반 독립 배포.

---

## 크로스클라우드 연결

통합 아키텍처의 핵심은 AWS 서빙 레이어가 GCP 데이터 레이어에 접근하는 크로스클라우드 연결이다.

### FAISS 인덱스: AWS BE ← GCS

AWS BE 컨테이너 기동 시 GCS에서 FAISS 인덱스(`faiss.index` + `metadata.pkl`)를 다운로드하여 인메모리로 로드한다.

| 방법 | 설명 | 채택 여부 |
|------|------|----------|
| **GCS S3호환 API** | GCS가 S3 호환 엔드포인트를 제공 — `boto3`(AWS SDK)로 GCS에 직접 접근 가능. AWS 코드 변경 최소화. | **1차 선택** |
| **GCS Signed URL** | GCS 객체에 대한 시간 제한 다운로드 URL 생성. BE에서 `httpx`/`requests`로 다운로드. | 대안 (단순) |
| **Storage Transfer Service** | GCP 관리형 서비스로 GCS → S3 자동 전송 후 S3에서 로드. | 대안 (대용량 시) |

**선택 근거**: GCS S3호환 API를 사용하면 BE 코드에서 `boto3` 클라이언트의 엔드포인트만 GCS로 지정하면 되므로, 기존 S3 접근 패턴을 그대로 유지할 수 있다. FAISS 인덱스는 수십~수백 MB 수준이므로 기동 시 한 번 다운로드하면 충분하다.

```python
# GCS S3호환 API 접근 예시 (BE 기동 시)
import boto3

gcs_client = boto3.client(
    "s3",
    endpoint_url="https://storage.googleapis.com",
    aws_access_key_id=GCS_HMAC_ACCESS_KEY,
    aws_secret_access_key=GCS_HMAC_SECRET_KEY,
)
gcs_client.download_file("rag-qna-eval-data", "index/faiss.index", "/tmp/faiss.index")
gcs_client.download_file("rag-qna-eval-data", "index/metadata.pkl", "/tmp/metadata.pkl")
```

### MongoDB: AWS BE ↔ GCP VM

AWS BE가 GCP Compute Engine VM의 MongoDB에 직접 쿼리한다.

| 항목 | 현재 구성 | 확장 시 |
|------|----------|--------|
| **접근 방식** | 공개 IP + 방화벽 규칙 (27017 포트, AWS ECS IP 대역 허용) | MongoDB Atlas 전환 |
| **용도** | 정책 메타데이터 조회 (`policies` 컬렉션), 수집 이력, API 사용 로그 | 동일 |
| **보안** | GCP 방화벽에서 소스 IP 제한 + MongoDB 인증 | Atlas VPC Peering |

**Atlas 전환 전략**: 현재는 GCP VM에 MongoDB를 직접 운영하여 비용을 절감한다(e2-small, GCP 크레딧 커버). 향후 트래픽 증가 또는 고가용성이 필요하면 MongoDB Atlas(프리티어 512MB 또는 유료)로 전환한다. Atlas는 GCP/AWS 양쪽에서 동일한 연결 문자열로 접근 가능하므로 코드 변경이 최소화된다.

### QA 평가 데이터셋

| 방법 | 설명 |
|------|------|
| **Git 레포 공유** | `data/eval/qa_pairs.json`이 레포에 포함되어 있어 양쪽에서 동일 데이터 사용 |
| **GCS 다운로드** | BE 기동 시 GCS에서 최신 QA 데이터셋 다운로드 (평가 데이터가 자주 갱신될 경우) |

---

## 공유 데이터 목록

| 데이터 | 위치 (GCP) | 포맷 | AWS 접근 방법 |
|--------|-----------|------|-------------|
| 수집된 정책 원본 | `gs://rag-qna-eval-data/policies/` | JSON, PDF | S3호환 API or Signed URL |
| FAISS 인덱스 | `gs://rag-qna-eval-data/index/` | `faiss.index` + `metadata.pkl` | **BE 기동 시 GCS에서 다운로드** (S3호환 API) |
| QA 평가 데이터셋 | `data/eval/qa_pairs.json` | JSON | Git 레포 공유 or GCS 다운로드 |
| 청크 데이터 | `gs://rag-qna-eval-data/chunks/` | JSON | 필요 시 S3호환 API |
| 정책 메타데이터 | MongoDB (`policies` 컬렉션) | BSON | **BE → GCP VM 직접 쿼리** (공개 IP + 방화벽) |
| 수집/API 이력 | MongoDB (`ingestion_logs`, `api_usage_logs`) | BSON | **BE → GCP VM 직접 쿼리** |

---

## 다이어그램

전체 아키텍처 다이어그램: [`docs/rag-qa-pipeline-multicloud.drawio`](rag-qa-pipeline-multicloud.drawio)

```
┌──────────────────────────────────────────┐     ┌──────────────────────────────────────────┐
│            AWS (서빙 + 평가)               │     │            GCP (데이터 파이프라인)           │
│                                          │     │                                          │
│  ECR ─→ ECS Fargate                      │     │  Cloud Scheduler (매일 1회)                │
│          ├─ FE: Streamlit (512Mi)         │     │    → Cloud Run Job #1 (Data Crawler)      │
│          └─ BE: FastAPI+FAISS (2Gi)      │     │        → 정부 사이트 크롤링                  │
│               │                          │     │                                          │
│  ALB ──→ FE ──httpx──→ BE                │     │  GCS (원본 + 인덱스)                       │
│               │                          │     │    ├─ policies/                           │
│  3-Stage Eval (BE 내부)                   │     │    └─ index/                              │
│    Stage1: RAGAS v0.4                    │     │         ↑                                 │
│    Stage2: LLM Judge                     │     │    Eventarc → Cloud Run Job #2             │
│    Stage3: DeepEval                      │     │              (Chunker/Embedder → FAISS)    │
│               │                          │     │                                          │
│  CloudWatch + Managed Grafana            │     │  Compute Engine (e2-small)                │
│               │                          │     │    └─ MongoDB + Grafana                   │
│               │    ┌─────────────────────┼─────┼─────────────┐                            │
│               │    │  Cross-Cloud         │     │             │                            │
│               ├────┤  FAISS Index Load  ←─┼─────┼── GCS       │                            │
│               └────┤  Metadata Query    ←─┼──→──┼── MongoDB   │                            │
│                    └─────────────────────┼─────┼─────────────┘                            │
│                                          │     │  Cloud Logging / Monitoring               │
└──────────────────────────────────────────┘     └──────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │  External LLM APIs    │
        │  (via LiteLLM)        │
        │  GPT-4o │ Claude      │
        │  Gemini │ Llama 3.2   │
        └─────────────────────── ┘
```
