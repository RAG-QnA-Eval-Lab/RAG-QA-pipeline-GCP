#!/usr/bin/env bash
# Cloud Run /health 엔드포인트 Uptime Check + 알림 설정.
# 사용법: bash scripts/setup_uptime_check.sh <ALERT_EMAIL>
#
# 사전 조건:
#   - gcloud CLI 인증 완료
#   - Cloud Monitoring API 활성화 (gcloud services enable monitoring.googleapis.com)
set -euo pipefail

PROJECT="rag-qna-eval"
REGION="asia-northeast3"
SERVICE_NAME="rag-youth-policy-api"
ALERT_EMAIL="${1:?Usage: $0 <alert-email>}"

echo "=== 1/4: Cloud Run 서비스 URL 확인 ==="
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format 'value(status.url)' 2>/dev/null || true)

if [ -z "$SERVICE_URL" ]; then
  echo "ERROR: Cloud Run 서비스 '$SERVICE_NAME'을 찾을 수 없습니다."
  exit 1
fi

HOSTNAME=$(echo "$SERVICE_URL" | sed 's|https://||')
echo "  서비스 URL: $SERVICE_URL"
echo "  호스트: $HOSTNAME"

echo ""
echo "=== 2/4: Uptime Check 생성 ==="
# 이미 존재하는지 확인
EXISTING=$(gcloud monitoring uptime list-configs \
  --project "$PROJECT" \
  --filter="displayName='RAG API Health Check'" \
  --format='value(name)' 2>/dev/null || true)

if [ -n "$EXISTING" ]; then
  echo "  이미 존재: $EXISTING (건너뜀)"
else
  gcloud monitoring uptime create \
    --project "$PROJECT" \
    --display-name="RAG API Health Check" \
    --resource-type=uptime-url \
    --hostname="$HOSTNAME" \
    --path="/health" \
    --port=443 \
    --protocol=HTTPS \
    --period=300 \
    --timeout=10s \
    --checker-type=STATIC_IP_CHECKERS \
    --selected-regions=ASIA_PACIFIC
  echo "  Uptime Check 생성 완료 (5분 간격, ASIA_PACIFIC 리전)"
fi

echo ""
echo "=== 3/4: 이메일 알림 채널 생성 ==="
CHANNEL_ID=$(gcloud beta monitoring channels list \
  --project "$PROJECT" \
  --filter="type='email' AND labels.email_address='$ALERT_EMAIL'" \
  --format='value(name)' 2>/dev/null | head -1 || true)

if [ -n "$CHANNEL_ID" ]; then
  echo "  이미 존재: $CHANNEL_ID (건너뜀)"
else
  CHANNEL_ID=$(gcloud beta monitoring channels create \
    --project "$PROJECT" \
    --display-name="RAG Admin Email" \
    --type=email \
    --channel-labels="email_address=$ALERT_EMAIL" \
    --format='value(name)')
  echo "  알림 채널 생성: $CHANNEL_ID"
fi

echo ""
echo "=== 4/4: 알림 정책 생성 ==="
EXISTING_POLICY=$(gcloud alpha monitoring policies list \
  --project "$PROJECT" \
  --filter="displayName='RAG API Down Alert'" \
  --format='value(name)' 2>/dev/null | head -1 || true)

if [ -n "$EXISTING_POLICY" ]; then
  echo "  이미 존재: $EXISTING_POLICY (건너뜀)"
else
  gcloud alpha monitoring policies create \
    --project "$PROJECT" \
    --display-name="RAG API Down Alert" \
    --condition-display-name="Health check failed" \
    --condition-filter='metric.type="monitoring.googleapis.com/uptime_check/check_passed" AND resource.type="uptime_url"' \
    --condition-threshold-value=1 \
    --condition-threshold-comparison=COMPARISON_LT \
    --condition-threshold-duration=300s \
    --notification-channels="$CHANNEL_ID" \
    --combiner=OR
  echo "  알림 정책 생성 완료 (5분 연속 실패 시 이메일 알림)"
fi

echo ""
echo "=== 완료 ==="
echo "  Uptime Check: https://console.cloud.google.com/monitoring/uptime?project=$PROJECT"
echo "  알림 정책: https://console.cloud.google.com/monitoring/alerting?project=$PROJECT"
