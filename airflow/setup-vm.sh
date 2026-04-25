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

echo "=== 1/7. 시스템 패키지 설치 ==="
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-dev \
  postgresql postgresql-client \
  git curl build-essential libpq-dev

echo "=== 2/7. PostgreSQL 설정 ==="
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='airflow'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER airflow WITH PASSWORD 'airflow';"
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
  pip install -e '.[ingestion,indexer,ko]'
"

echo "=== 6/7. Airflow 환경변수 + DB 초기화 ==="
# 환경변수 설정 파일
cat > ${AIRFLOW_HOME}/airflow.env << 'ENVEOF'
export AIRFLOW_HOME=/opt/airflow
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Seoul
export AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=1
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@localhost:5432/airflow
export AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
export AIRFLOW__WEBSERVER__RBAC=True
export AIRFLOW__WEBSERVER__EXPOSE_CONFIG=False
export AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL=60
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs
ENVEOF
chown ${AIRFLOW_USER}:${AIRFLOW_USER} ${AIRFLOW_HOME}/airflow.env

sudo -u ${AIRFLOW_USER} bash -c "
  source ${AIRFLOW_HOME}/airflow.env
  source ${AIRFLOW_HOME}/venv/bin/activate
  airflow db migrate
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password 1129
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
echo "계정: admin / 1129"
echo ""
echo "DAG 동기화: 5분마다 git pull (${REPO_DIR})"
echo "DAG 경로: ${AIRFLOW_HOME}/dags → ${REPO_DIR}/dags (심링크)"
