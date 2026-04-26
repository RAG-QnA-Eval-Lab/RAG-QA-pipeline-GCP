# Phase 6 Runbook — GCP 배포·모니터링·실험

## 1. Cloud Run 배포

- API: `.github/workflows/deploy-api.yml`
  - GCS `index/faiss.index`, `index/metadata.pkl`을 기동 시 `/app/data/index`로 다운로드
  - `MONGODB_URI`, `OPENAI_API_KEY`, `HUGGINGFACE_API_KEY`는 Secret Manager에서 주입
  - `ENABLE_CLOUD_MONITORING=true`로 커스텀 메트릭 전송
- UI: `.github/workflows/deploy-ui.yml`
  - Cloud Run `PORT` 환경변수 기반으로 Streamlit 실행
  - GitHub repository variable `API_BASE_URL`에 API 서비스 URL 설정

## 2. 헬스체크

`GET /health`는 다음을 확인한다.

- FAISS 로드 여부/문서 수/인덱스 수정 시각
- MongoDB ping 및 수집 파이프라인 요약
- GCS 인덱스 객체 접근 가능 여부
- uptime/version

Cloud Monitoring Uptime Check 대상: `https://<api-url>/health`

## 3. Grafana

대시보드 JSON: `infra/grafana/rag-dashboard.json`

패널 5개:
1. Cloud Run 요청 수/지연시간
2. RAG 검색·생성 지연시간
3. LLM 토큰·비용 추정치
4. MongoDB `api_usage_logs` 모델별 비용 트래커
5. MongoDB `ingestion_logs` 데이터 적재 신선도

## 4. 실험 실행

```bash
# 스모크: 생성만 5개
python scripts/run_phase6_experiments.py --experiment all --limit 5 --skip-evaluation

# 모델 비교 전체 평가
python scripts/run_phase6_experiments.py --experiment model --limit 100

# 검색 전략 비교
python scripts/run_phase6_experiments.py --experiment strategy --limit 100

# RAG vs No-RAG
python scripts/run_phase6_experiments.py --experiment rag --limit 100
```

출력은 `data/results/phase6/<run_id>/` 아래에 JSON/HTML로 저장된다.
