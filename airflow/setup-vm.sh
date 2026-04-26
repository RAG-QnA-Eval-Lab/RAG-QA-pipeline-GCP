#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Airflow VM 프로비저닝 스크립트
# 대상: GCP Compute Engine (e2-standard-2, Ubuntu 24.04/25.04)
# 용도: Apache Airflow 2.9.x + PostgreSQL + LocalExecutor
#
# 사용법:
#   1. VM 생성:
#      gcloud compute instances create rag-airflow-vm \
#        --zone=asia-northeast3-a \
#        --machine-type=e2-standard-2 \
#        --image-family=ubuntu-2404-lts-amd64 \
#        --image-project=ubuntu-os-cloud \
#        --boot-disk-size=30GB \
#        --service-account=SA_EMAIL \
#        --scopes=cloud-platform \
#        --tags=airflow-server
#
#   2. SSH 접속 후 실행:
#      sudo bash setup-vm.sh
# ============================================================

AIRFLOW_HOME="/opt/airflow"
AIRFLOW_USER="airflow"
REPO_URL="https://github.com/Daehyun-Bigbread/RAG-QA-pipeline-GCP.git"
REPO_DIR="/opt/rag-pipeline"
GCP_PROJECT="${GCP_PROJECT:-rag-qna-eval}"
GCS_BUCKET="${GCS_BUCKET:-rag-qna-eval-data}"
VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-rag-qna-eval}"
VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-asia-northeast3}"

AIRFLOW_DB_PASSWORD_SECRET="${AIRFLOW_DB_PASSWORD_SECRET:-airflow-db-password}"
AIRFLOW_ADMIN_PASSWORD_SECRET="${AIRFLOW_ADMIN_PASSWORD_SECRET:-airflow-admin-password}"
MONGODB_URI_SECRET="${MONGODB_URI_SECRET:-mongodb-uri}"
DATA_PORTAL_API_KEY_SECRET="${DATA_PORTAL_API_KEY_SECRET:-data-portal-api-key}"
OPENAI_API_KEY_SECRET="${OPENAI_API_KEY_SECRET:-openai-api-key}"
HUGGINGFACE_API_KEY_SECRET="${HUGGINGFACE_API_KEY_SECRET:-huggingface-api-key}"

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "필수 명령 없음: ${cmd}" >&2
    exit 1
  fi
}

read_secret() {
  local secret_name="$1"
  gcloud secrets versions access latest \
    --secret="${secret_name}" \
    --project="${GCP_PROJECT}" \
    2>/dev/null
}

read_optional_secret() {
  local secret_name="$1"
  gcloud secrets versions access latest \
    --secret="${secret_name}" \
    --project="${GCP_PROJECT}" \
    2>/dev/null || true
}

shell_escape() {
  printf "%q" "$1"
}

require_command gcloud

DB_PASSWORD="$(read_secret "${AIRFLOW_DB_PASSWORD_SECRET}")"
ADMIN_PASSWORD="$(read_secret "${AIRFLOW_ADMIN_PASSWORD_SECRET}")"
MONGODB_URI="$(read_secret "${MONGODB_URI_SECRET}")"
DATA_PORTAL_API_KEY="$(read_secret "${DATA_PORTAL_API_KEY_SECRET}")"
OPENAI_API_KEY="$(read_optional_secret "${OPENAI_API_KEY_SECRET}")"
HUGGINGFACE_API_KEY="$(read_optional_secret "${HUGGINGFACE_API_KEY_SECRET}")"

: "${DB_PASSWORD:?Secret Manager에서 Airflow DB 비밀번호를 읽지 못했습니다.}"
: "${ADMIN_PASSWORD:?Secret Manager에서 Airflow 관리자 비밀번호를 읽지 못했습니다.}"
: "${MONGODB_URI:?Secret Manager에서 MongoDB URI를 읽지 못했습니다.}"
: "${DATA_PORTAL_API_KEY:?Secret Manager에서 공공데이터포털 API 키를 읽지 못했습니다.}"

SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow:${DB_PASSWORD}@localhost:5432/airflow"
SQL_ALCHEMY_CONN_ESCAPED="$(shell_escape "${SQL_ALCHEMY_CONN}")"
GCP_PROJECT_ESCAPED="$(shell_escape "${GCP_PROJECT}")"
GCS_BUCKET_ESCAPED="$(shell_escape "${GCS_BUCKET}")"
VERTEXAI_PROJECT_ESCAPED="$(shell_escape "${VERTEXAI_PROJECT}")"
VERTEXAI_LOCATION_ESCAPED="$(shell_escape "${VERTEXAI_LOCATION}")"
MONGODB_URI_ESCAPED="$(shell_escape "${MONGODB_URI}")"
DATA_PORTAL_API_KEY_ESCAPED="$(shell_escape "${DATA_PORTAL_API_KEY}")"
OPENAI_API_KEY_ESCAPED="$(shell_escape "${OPENAI_API_KEY}")"
HUGGINGFACE_API_KEY_ESCAPED="$(shell_escape "${HUGGINGFACE_API_KEY}")"

echo "=== 1/7. 시스템 패키지 설치 ==="
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-dev \
  postgresql postgresql-client \
  git curl build-essential libpq-dev \
  mecab libmecab-dev mecab-ipadic-utf8

echo "=== 2/7. PostgreSQL 설정 ==="
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='airflow'" | grep -q 1 || \
  sudo -u postgres psql -v db_password="${DB_PASSWORD}" -c "CREATE USER airflow WITH PASSWORD :'db_password';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='airflow'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE airflow OWNER airflow;"

echo "=== 3/7. Airflow 시스템 사용자 생성 ==="
id -u ${AIRFLOW_USER} &>/dev/null || useradd -r -m -d ${AIRFLOW_HOME} -s /bin/bash ${AIRFLOW_USER}
mkdir -p ${AIRFLOW_HOME}/{dags,logs,plugins}
chown -R ${AIRFLOW_USER}:${AIRFLOW_USER} ${AIRFLOW_HOME}

echo "=== 4/7. 프로젝트 레포 클론 ==="
if [ -d "${REPO_DIR}" ]; then
  cd ${REPO_DIR} && git pull
else
  git clone ${REPO_URL} ${REPO_DIR}
fi
chown -R ${AIRFLOW_USER}:${AIRFLOW_USER} ${REPO_DIR}

echo "=== 5/7. Python 가상환경 + Airflow 설치 ==="
sudo -u ${AIRFLOW_USER} bash -c "
  python3 -m venv ${AIRFLOW_HOME}/venv
  source ${AIRFLOW_HOME}/venv/bin/activate

  pip install --upgrade pip setuptools wheel

  # Airflow + 프로바이더
  pip install -r ${REPO_DIR}/airflow/requirements-airflow.txt

  # 프로젝트 패키지 (DAG에서 import 필요)
  cd ${REPO_DIR}
  pip install -e '.[ingestion,indexer,ko,eval]'
"

echo "=== 6/7. Airflow 환경변수 + DB 초기화 ==="
# 환경변수 설정 파일
cat > ${AIRFLOW_HOME}/airflow.env << ENVEOF
AIRFLOW_HOME=/opt/airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Seoul
AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=1
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=${SQL_ALCHEMY_CONN_ESCAPED}
AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
AIRFLOW__WEBSERVER__RBAC=True
AIRFLOW__WEBSERVER__EXPOSE_CONFIG=False
AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL=60
AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs
PYTHONPATH=${REPO_DIR}
GCP_PROJECT=${GCP_PROJECT_ESCAPED}
GCS_BUCKET=${GCS_BUCKET_ESCAPED}
VERTEXAI_PROJECT=${VERTEXAI_PROJECT_ESCAPED}
VERTEXAI_LOCATION=${VERTEXAI_LOCATION_ESCAPED}
MONGODB_URI=${MONGODB_URI_ESCAPED}
DATA_PORTAL_API_KEY=${DATA_PORTAL_API_KEY_ESCAPED}
OPENAI_API_KEY=${OPENAI_API_KEY_ESCAPED}
HUGGINGFACE_API_KEY=${HUGGINGFACE_API_KEY_ESCAPED}
ENVEOF
chown ${AIRFLOW_USER}:${AIRFLOW_USER} ${AIRFLOW_HOME}/airflow.env
chmod 600 ${AIRFLOW_HOME}/airflow.env

export ADMIN_PASSWORD
sudo -E -u ${AIRFLOW_USER} bash -c "
  set -a
  source ${AIRFLOW_HOME}/airflow.env
  set +a
  source ${AIRFLOW_HOME}/venv/bin/activate
  airflow db migrate
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password \"\${ADMIN_PASSWORD}\"
"

echo "=== 7/7. systemd 서비스 등록 ==="

# DAG 동기화 심링크
ln -sfn ${REPO_DIR}/dags ${AIRFLOW_HOME}/dags

# Airflow Webserver 서비스
cat > /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Airflow Webserver
After=postgresql.service
Wants=postgresql.service

[Service]
User=${AIRFLOW_USER}
Group=${AIRFLOW_USER}
EnvironmentFile=${AIRFLOW_HOME}/airflow.env
ExecStart=${AIRFLOW_HOME}/venv/bin/airflow webserver
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Airflow Scheduler 서비스
cat > /etc/systemd/system/airflow-scheduler.service << EOF
[Unit]
Description=Airflow Scheduler
After=postgresql.service
Wants=postgresql.service

[Service]
User=${AIRFLOW_USER}
Group=${AIRFLOW_USER}
EnvironmentFile=${AIRFLOW_HOME}/airflow.env
ExecStart=${AIRFLOW_HOME}/venv/bin/airflow scheduler
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# DAG 동기화 cron (5분마다 git pull)
cat > /etc/cron.d/airflow-dag-sync << EOF
*/5 * * * * ${AIRFLOW_USER} cd ${REPO_DIR} && git pull --ff-only >> ${AIRFLOW_HOME}/logs/dag-sync.log 2>&1
EOF

systemctl daemon-reload
systemctl enable airflow-webserver airflow-scheduler
systemctl start airflow-webserver airflow-scheduler

echo ""
echo "=== 설치 완료 ==="
echo "Airflow UI: http://<VM_EXTERNAL_IP>:8080"
echo "계정: admin / <AIRFLOW_ADMIN_PASSWORD>"
echo ""
echo "DAG 동기화: 5분마다 git pull (${REPO_DIR})"
echo "DAG 경로: ${AIRFLOW_HOME}/dags → ${REPO_DIR}/dags (심링크)"
