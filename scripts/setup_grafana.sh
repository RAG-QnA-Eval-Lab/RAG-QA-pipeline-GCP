#!/usr/bin/env bash
# Grafana 대시보드 프로비저닝 스크립트.
# MongoDB VM (rag-mongodb-vm)에서 실행한다.
#
# 사용법: bash scripts/setup_grafana.sh
#
# 사전 조건:
#   - Grafana 이미 설치 및 실행 중 (systemctl status grafana-server)
#   - MongoDB 로컬 접속 가능 (localhost:27017)
set -euo pipefail

GRAFANA_HOME="/etc/grafana"
GRAFANA_DASHBOARDS="/var/lib/grafana/dashboards"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== 1/4: MongoDB Grafana 플러그인 설치 ==="
if grafana-cli plugins ls 2>/dev/null | grep -q "grafana-mongodb-datasource"; then
  echo "  이미 설치됨 (건너뜀)"
else
  sudo grafana-cli plugins install grafana-mongodb-datasource
  echo "  플러그인 설치 완료"
fi

echo ""
echo "=== 2/4: 프로비저닝 설정 복사 ==="
sudo cp "$REPO_ROOT/monitoring/grafana/provisioning/datasources.yml" \
  "$GRAFANA_HOME/provisioning/datasources/rag-datasources.yml"
sudo cp "$REPO_ROOT/monitoring/grafana/provisioning/dashboards.yml" \
  "$GRAFANA_HOME/provisioning/dashboards/rag-dashboards.yml"
echo "  프로비저닝 파일 복사 완료"

echo ""
echo "=== 3/4: 대시보드 JSON 복사 ==="
sudo mkdir -p "$GRAFANA_DASHBOARDS"
sudo cp "$REPO_ROOT/monitoring/grafana/dashboards/rag-pipeline.json" \
  "$GRAFANA_DASHBOARDS/rag-pipeline.json"
echo "  대시보드 복사 완료"

echo ""
echo "=== 4/4: Grafana 재시작 ==="
sudo systemctl restart grafana-server
sleep 2
if systemctl is-active --quiet grafana-server; then
  echo "  Grafana 재시작 성공"
else
  echo "  WARNING: Grafana 재시작 실패. 로그 확인: sudo journalctl -u grafana-server -n 20"
fi

GRAFANA_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== 완료 ==="
echo "  대시보드: http://${GRAFANA_IP}:3000/d/rag-youth-policy"
echo "  기본 로그인: admin / admin"
echo ""
echo "  참고: Google Cloud Monitoring 데이터 소스를 사용하려면"
echo "  서비스 계정 키(JSON)를 Grafana 데이터 소스 설정에서 구성하세요."
