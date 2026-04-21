# GCP 파트 구현 TODO

> plan.md 기준 GCP Offline Pipeline 구축에 필요한 작업 목록
> 작성일: 2026-04-21

---

## 현재 완료된 것 (로컬 동작 수준)

| 구분 | 파일 | 상태 |
|------|------|------|
| Policy 스키마 + 검증 | `src/ingestion/collectors/base.py` | ✅ 완료 |
| 공공데이터포털 수집기 | `src/ingestion/collectors/data_portal.py` | ✅ 완료 |
| 문서 로더 (JSON/PDF/TXT) | `src/ingestion/loader.py` | ✅ 완료 |
| 토큰 기반 청킹 | `src/ingestion/chunker.py` | ✅ 완료 |
| 임베딩 래퍼 (LiteLLM) | `src/ingestion/embedder.py` | ✅ 완료 |
| FAISS 인덱스 빌드 | `src/ingestion/pipeline.py` | ✅ 완료 (로컬 파일만) |
| MongoDB 클라이언트 | `src/ingestion/mongo_client.py` | ✅ 완료 (파이프라인 미연동) |
| 테스트 커버리지 | `tests/test_*.py` | ✅ 119 passed |

---

## 구현 TODO (우선순위순)

### 1. GCS 클라이언트 모듈 (신규) ⭐ 최우선

**파일**: `src/ingestion/gcs_client.py`

```python
# 필요 기능
class GCSClient:
    def __init__(self, bucket_name: str): ...
    
    def upload_json(self, gcs_path: str, data: dict | list) -> str:
        """정책 JSON 업로드. 반환: gs:// URI"""
    
    def upload_file(self, local_path: Path, gcs_path: str) -> str:
        """로컬 파일 업로드 (FAISS index, metadata.pkl)"""
    
    def download_file(self, gcs_path: str, local_path: Path) -> Path:
        """GCS → 로컬 다운로드"""
    
    def download_json(self, gcs_path: str) -> dict | list:
        """JSON 파일 다운로드 + 파싱"""
    
    def list_blobs(self, prefix: str) -> list[str]:
        """prefix로 파일 목록 조회"""
    
    def exists(self, gcs_path: str) -> bool:
        """파일 존재 여부"""
```

**GCS 버킷 구조** (plan.md 기준):
```
gs://rag-qna-eval-data/
├── policies/
│   ├── raw/                          # 원본 수집 데이터
│   │   ├── data_portal_policies.json
│   │   ├── youthgo_policies.json
│   │   └── kosaf_policies.json
│   └── processed/                    # 정규화된 정책 JSON
│       └── all_policies.json
└── index/
    ├── faiss.index                   # FAISS 벡터 인덱스
    └── metadata.pkl                  # 청크 메타데이터
```

**체크리스트**:
- [x] `google-cloud-storage` import 및 Client 초기화
- [x] JSON 업로드/다운로드 (UTF-8, ensure_ascii=False)
- [x] 바이너리 파일 업로드/다운로드 (FAISS index, pickle)
- [x] 에러 핸들링 (버킷 없음, 권한 없음, 네트워크)
- [x] 단위 테스트 (`tests/test_gcs_client.py`) — 11 passed

---

### 2. 수집 CLI에 GCS + MongoDB 연동 (수정)

**파일**: `scripts/collect_policies.py`

현재:
```python
# 로컬 JSON 저장만
save_policies_json(policy_dicts, output_path)
```

변경 후:
```python
from src.ingestion.gcs_client import GCSClient
from src.ingestion.mongo_client import PolicyMetadataStore

gcs = GCSClient(settings.gcs_bucket)
mongo = PolicyMetadataStore()

# 1. 로컬 JSON 저장 (캐시)
save_policies_json(policy_dicts, local_path)

# 2. GCS 업로드
gcs_path = f"policies/raw/{source}_policies.json"
gcs.upload_json(gcs_path, policy_dicts)

# 3. MongoDB 메타데이터 upsert
metadata_list = [
    {
        "policy_id": p["policy_id"],
        "title": p["title"],
        "category": p["category"],
        "source_name": source,
        "gcs_path": f"gs://{settings.gcs_bucket}/{gcs_path}",
        "status": "active",
    }
    for p in policy_dicts
]
mongo.upsert_policies_batch(metadata_list)

# 4. 수집 이력 기록
mongo.log_ingestion(
    source=source,
    collected_count=len(policy_dicts),
    valid_count=len(valid_policies),
    gcs_paths=[f"gs://{settings.gcs_bucket}/{gcs_path}"],
)
```

**체크리스트**:
- [x] GCSClient 호출 추가
- [x] PolicyMetadataStore.upsert_policies_batch() 호출
- [x] PolicyMetadataStore.log_ingestion() 호출
- [x] `--skip-gcs`, `--skip-mongo` 플래그 (로컬 테스트용)
- [x] 환경변수 검증 (GCS_BUCKET, MONGODB_URI)

---

### 3. 인덱싱 파이프라인에 GCS 입출력 (수정)

**파일**: `src/ingestion/pipeline.py`

현재:
```python
# 로컬 입력/출력만
documents = load_directory(input_dir)
faiss.write_index(index, str(index_path))
```

변경 후:
```python
def build_index_from_gcs(
    bucket: str,
    input_prefix: str = "policies/processed/",
    output_prefix: str = "index/",
) -> dict:
    """GCS에서 정책 로드 → 인덱스 빌드 → GCS 업로드"""
    gcs = GCSClient(bucket)
    
    # 1. GCS에서 정책 다운로드
    policies = gcs.download_json(f"{input_prefix}all_policies.json")
    
    # 2. 인덱스 빌드 (기존 로직)
    result = build_index_from_policies(policies, local_temp_dir)
    
    # 3. GCS 업로드
    gcs.upload_file(local_temp_dir / "faiss.index", f"{output_prefix}faiss.index")
    gcs.upload_file(local_temp_dir / "metadata.pkl", f"{output_prefix}metadata.pkl")
    
    return result
```

**CLI 옵션 추가**:
```bash
# 로컬 모드 (기존)
python -m src.ingestion.pipeline --input data/policies/raw --output data/index

# GCS 모드 (신규)
python -m src.ingestion.pipeline --gcs --bucket rag-qna-eval-data
```

**체크리스트**:
- [x] `build_index_from_gcs()` 함수 추가
- [x] argparse에 `--gcs`, `--bucket` 옵션
- [x] 임시 디렉토리 사용 (tempfile.TemporaryDirectory)
- [x] 업로드 완료 후 로컬 임시 파일 정리

---

### 4. Cloud Run Job용 Dockerfile 2종 (신규)

#### 4.1 Collector Job

**파일**: `Dockerfile.collector`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[crawl]"

# 소스 복사
COPY config/ config/
COPY src/ingestion/ src/ingestion/
COPY scripts/collect_policies.py scripts/

# 환경변수는 Cloud Run에서 주입
# DATA_PORTAL_API_KEY, GCS_BUCKET, MONGODB_URI

CMD ["python", "scripts/collect_policies.py", "--all"]
```

#### 4.2 Indexer Job

**파일**: `Dockerfile.indexer`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치 (임베딩, FAISS, 한국어)
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[ko]"

# 소스 복사
COPY config/ config/
COPY src/ingestion/ src/ingestion/

# 환경변수는 Cloud Run에서 주입
# OPENAI_API_KEY, GCS_BUCKET

CMD ["python", "-m", "src.ingestion.pipeline", "--gcs", "--bucket", "${GCS_BUCKET}"]
```

**체크리스트**:
- [x] `Dockerfile.collector` 작성
- [x] `Dockerfile.indexer` 작성
- [x] Cloud Build 빌드 테스트 완료
- [x] 필요 환경변수 목록 문서화

---

### 5. Cloud Run Job 배포 워크플로 (신규)

**파일**: `.github/workflows/deploy-jobs.yml`

```yaml
name: Deploy Cloud Run Jobs
on:
  push:
    branches: [main]
    paths:
      - "src/ingestion/**"
      - "scripts/collect_policies.py"
      - "Dockerfile.collector"
      - "Dockerfile.indexer"
  workflow_dispatch:  # 수동 트리거

env:
  PROJECT_ID: rag-qna-eval
  REGION: asia-northeast3
  REGISTRY: asia-northeast3-docker.pkg.dev

jobs:
  deploy-collector:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Build and Deploy Collector Job
        run: |
          gcloud builds submit \
            --tag ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/repo/collector:${{ github.sha }} \
            -f Dockerfile.collector
          
          gcloud run jobs deploy rag-collector \
            --image ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/repo/collector:${{ github.sha }} \
            --region ${{ env.REGION }} \
            --memory 512Mi \
            --set-env-vars "DATA_PORTAL_API_KEY=${{ secrets.DATA_PORTAL_API_KEY }}" \
            --set-env-vars "GCS_BUCKET=rag-qna-eval-data" \
            --set-env-vars "MONGODB_URI=${{ secrets.MONGODB_URI }}"

  deploy-indexer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Build and Deploy Indexer Job
        run: |
          gcloud builds submit \
            --tag ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/repo/indexer:${{ github.sha }} \
            -f Dockerfile.indexer
          
          gcloud run jobs deploy rag-indexer \
            --image ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/repo/indexer:${{ github.sha }} \
            --region ${{ env.REGION }} \
            --memory 2Gi \
            --set-env-vars "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" \
            --set-env-vars "GCS_BUCKET=rag-qna-eval-data"
```

**GitHub Secrets 필요**:
- `GCP_SA_KEY` — 서비스 계정 JSON 키
- `DATA_PORTAL_API_KEY` — 공공데이터포털 API 키
- `MONGODB_URI` — MongoDB 연결 URI
- `OPENAI_API_KEY` — 임베딩용

**체크리스트**:
- [x] 워크플로 파일 작성 (`.github/workflows/deploy-jobs.yml`)
- [x] GitHub Secrets 등록 (GCP_SA_KEY, OPENAI_API_KEY, DATA_PORTAL_API_KEY, MONGODB_URI)
- [x] 수동 배포 + Job 실행 테스트 완료

---

### 6. Cloud Scheduler 설정

**목적**: 매일 02:00 KST에 Collector Job 실행

```bash
# 서비스 계정 생성
gcloud iam service-accounts create scheduler-sa \
  --display-name="Cloud Scheduler Service Account"

# Cloud Run Job 실행 권한 부여
gcloud projects add-iam-policy-binding rag-qna-eval \
  --member="serviceAccount:scheduler-sa@rag-qna-eval.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Scheduler Job 생성
gcloud scheduler jobs create http rag-daily-collect \
  --schedule="0 2 * * *" \
  --time-zone="Asia/Seoul" \
  --uri="https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/rag-qna-eval/jobs/rag-collector:run" \
  --http-method=POST \
  --location=asia-northeast3 \
  --oidc-service-account-email=scheduler-sa@rag-qna-eval.iam.gserviceaccount.com
```

**체크리스트**:
- [x] 서비스 계정 생성 (scheduler-invoker)
- [x] IAM 권한 부여 (roles/run.invoker)
- [x] Scheduler Job 생성 (rag-daily-collector 02:00 + rag-daily-indexer 03:00 KST)
- [x] 수동 실행 테스트 (gcloud run jobs execute로 검증 완료)

---

### 7. Eventarc 트리거 설정

**목적**: GCS 정책 업로드 완료 → Indexer Job 자동 실행

```bash
# 서비스 계정 생성
gcloud iam service-accounts create eventarc-sa \
  --display-name="Eventarc Service Account"

# 권한 부여
gcloud projects add-iam-policy-binding rag-qna-eval \
  --member="serviceAccount:eventarc-sa@rag-qna-eval.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding rag-qna-eval \
  --member="serviceAccount:eventarc-sa@rag-qna-eval.iam.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"

# Eventarc 트리거 생성
gcloud eventarc triggers create rag-index-trigger \
  --destination-run-job=rag-indexer \
  --destination-run-region=asia-northeast3 \
  --location=asia-northeast3 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=rag-qna-eval-data" \
  --event-filters-path-pattern="prefix=policies/processed/" \
  --service-account=eventarc-sa@rag-qna-eval.iam.gserviceaccount.com
```

**동작 흐름**:
```
Collector Job 완료
  → GCS policies/processed/all_policies.json 업로드
    → Eventarc 감지 (object.finalized)
      → Indexer Job 자동 실행
        → FAISS 인덱스 재빌드
          → GCS index/ 업로드
```

**체크리스트**:
- [x] 서비스 계정 생성 + 권한 (eventarc-invoker, roles/run.invoker + roles/eventarc.eventReceiver)
- [x] Eventarc → Cloud Run Job 직접 트리거 미지원 확인 → Scheduler 시간차(03:00 KST)로 대체
- [ ] 테스트 파일 업로드로 트리거 동작 확인 (N/A — Scheduler 방식)

---

### 8. MongoDB VM 설정

**현재 상태**: `rag-mongo-vm` (e2-small, 중지 상태)

#### 8.1 VM 시작 + MongoDB 설치

```bash
# VM 시작
gcloud compute instances start rag-mongo-vm --zone=asia-northeast3-a

# SSH 접속
gcloud compute ssh rag-mongo-vm --zone=asia-northeast3-a

# VM 내부에서 MongoDB 설치
sudo apt-get update
sudo apt-get install -y gnupg curl

# MongoDB 7.0 Community Edition
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt-get update
sudo apt-get install -y mongodb-org

# 시작 + 자동 시작 설정
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### 8.2 방화벽 규칙

```bash
# 개발용 (특정 IP만 허용)
gcloud compute firewall-rules create allow-mongodb \
  --allow=tcp:27017 \
  --target-tags=mongodb \
  --source-ranges=YOUR_IP/32 \
  --description="MongoDB access from developer IP"

# Grafana용 (VM 내부)
gcloud compute firewall-rules create allow-grafana \
  --allow=tcp:3000 \
  --target-tags=mongodb \
  --source-ranges=YOUR_IP/32 \
  --description="Grafana dashboard access"
```

#### 8.3 외부 접속 설정

```bash
# /etc/mongod.conf 수정
sudo nano /etc/mongod.conf

# bindIp를 0.0.0.0으로 변경
net:
  port: 27017
  bindIp: 0.0.0.0

# 재시작
sudo systemctl restart mongod
```

#### 8.4 연결 테스트

```bash
# 외부 IP 확인
gcloud compute instances describe rag-mongo-vm \
  --zone=asia-northeast3-a \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

# 로컬에서 연결 테스트
mongosh "mongodb://EXTERNAL_IP:27017/rag_youth_policy"
```

**체크리스트**:
- [x] VM 시작 (34.50.21.132)
- [x] MongoDB 7.0.31 설치
- [x] 방화벽 규칙 설정 (allow-mongodb, tcp:27017, 0.0.0.0/0 + auth)
- [x] 외부 접속 설정 (bindIp: 0.0.0.0, authorization: enabled, ragadmin 유저)
- [x] CLI에서 연결 확인 (300건 policies, 1건 ingestion_logs)
- [x] `.env` MONGODB_URI에 실제 VM IP 반영 (34.50.21.132)

---

### 9. 추가 수집기 (선택)

plan.md에 계획된 4개 수집기 중 1개만 구현됨.

| 수집기 | 파일 | 상태 | 우선순위 |
|--------|------|------|----------|
| 공공데이터포털 API | `collectors/data_portal.py` | ✅ 완료 | - |
| 온통청년 (크롤링) | `collectors/youthgo.py` | ❌ 미구현 | 2차 |
| 한국장학재단 (크롤링) | `collectors/kosaf.py` | ❌ 미구현 | 2차 |
| 정부 PDF 보고서 | `collectors/pdf_reports.py` | ❌ 미구현 | 3차 |

**참고**: 공공데이터포털 API가 온통청년과 동일 데이터를 제공하므로, 추가 수집기 없이도 기본 파이프라인 검증 가능.

---

### 10. Cloud Monitoring 커스텀 메트릭 (선택)

**파일**: `src/ingestion/metrics.py`

```python
from google.cloud import monitoring_v3

def report_ingestion_metrics(
    source: str,
    collected_count: int,
    valid_count: int,
    duration_ms: int,
):
    """Cloud Monitoring에 수집 메트릭 전송"""
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{settings.gcp_project}"
    
    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/rag/ingestion_count"
    series.metric.labels["source"] = source
    # ... 메트릭 전송
```

---

## 실행 순서 체크리스트

```
Phase 1: GCS 연동 (로컬 테스트)
├── [x] 1. gcs_client.py 구현
├── [x] 2. collect_policies.py에 GCS 업로드 추가
├── [x] 3. pipeline.py에 GCS 입출력 추가
└── [x] 4. GCS 업/다운로드 테스트 (Cloud Run Job E2E 검증 완료)

Phase 2: MongoDB 연동
├── [x] 5. VM 시작 + MongoDB 7.0 설치 (rag-mongo-vm, 34.50.21.132)
├── [x] 6. 방화벽 + 외부 접속 설정 (bindIp: 0.0.0.0, auth enabled, ragadmin 유저)
├── [x] 7. collect_policies.py에 MongoDB 호출 추가
└── [x] 8. MongoDB 데이터 확인 (300건 policies + 1건 ingestion_logs)

Phase 3: Cloud Run Job 배포
├── [x] 9. Dockerfile.collector 작성 + 빌드 테스트
├── [x] 10. Dockerfile.indexer 작성 + 빌드 테스트
├── [x] 11. deploy-jobs.yml 워크플로 작성
├── [x] 12. GitHub Secrets 등록 (GCP_SA_KEY, OPENAI_API_KEY, DATA_PORTAL_API_KEY, MONGODB_URI)
└── [x] 13. 수동 배포 테스트 (collector: 300건 수집, indexer: 374청크 인덱싱 완료)

Phase 4: 자동화 (Scheduler + Eventarc)
├── [x] 14. Cloud Scheduler 설정 (rag-daily-collector 02:00, rag-daily-indexer 03:00 KST)
├── [x] 15. Eventarc → Scheduler 대체 (Cloud Run Job 직접 트리거 미지원, Scheduler 시간차로 대체)
└── [x] 16. End-to-End 테스트 완료 (수집 300건 → GCS + MongoDB → 인덱싱 374청크 → FAISS 2.55MiB)
```

---

## 예상 소요 시간

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| 1 | GCS 연동 | 2-3시간 |
| 2 | MongoDB 연동 | 1-2시간 |
| 3 | Cloud Run Job 배포 | 2-3시간 |
| 4 | Scheduler + Eventarc | 1-2시간 |
| **합계** | | **6-10시간** |

---

## 참고 명령어

```bash
# GCS 업로드 테스트
gsutil cp data/policies/raw/data_portal_policies.json gs://rag-qna-eval-data/policies/raw/

# Cloud Run Job 수동 실행
gcloud run jobs execute rag-collector --region=asia-northeast3

# Job 실행 로그 확인
gcloud run jobs executions logs rag-collector --region=asia-northeast3

# Scheduler Job 수동 실행
gcloud scheduler jobs run rag-daily-collect --location=asia-northeast3
```
