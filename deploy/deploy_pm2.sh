#!/usr/bin/env bash
# ============================================================
# deploy_pm2.sh
# PM2를 사용하여 stock-scheduler를 백그라운드로 실행합니다.
#
# 사전 조건:
#   sudo apt install -y nodejs npm
#   sudo npm install -g pm2
#
# 사용법:
#   1. 아래 변수를 실제 환경에 맞게 수정하세요.
#   2. chmod +x deploy_pm2.sh && ./deploy_pm2.sh
# ============================================================

set -euo pipefail

# ──────────────────────────────────────────────────────────
# ✏️  실제 환경에 맞게 수정하세요
# ──────────────────────────────────────────────────────────
PROJECT_DIR="/home/ubuntu/stock_monitor"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
APP_NAME="stock-scheduler"
# ──────────────────────────────────────────────────────────

echo "=================================================="
echo "  Stock Monitor — PM2 등록 시작"
echo "=================================================="

# 기존에 동일 이름으로 실행 중인 프로세스가 있으면 삭제
if pm2 describe "${APP_NAME}" &>/dev/null; then
    echo "[사전 정리] 기존 PM2 프로세스 삭제..."
    pm2 delete "${APP_NAME}"
fi

# PM2로 스케줄러 실행
echo "[1/3] PM2로 스케줄러 시작..."
pm2 start "${PROJECT_DIR}/scheduler.py" \
    --name "${APP_NAME}" \
    --interpreter "${VENV_PYTHON}" \
    --cwd "${PROJECT_DIR}"

# 서버 재부팅 시 자동 복구 등록
echo "[2/3] 부팅 자동 시작 설정..."
pm2 save
pm2 startup | tail -1 | bash || true   # startup 명령어 자동 실행

# 상태 확인
echo "[3/3] 프로세스 상태 확인..."
pm2 list

echo ""
echo "=================================================="
echo "  ✅ PM2 등록 완료!"
echo ""
echo "  📋 유용한 관리 명령어:"
echo "  pm2 list                          # 전체 프로세스 목록"
echo "  pm2 logs ${APP_NAME}              # 실시간 로그"
echo "  pm2 stop   ${APP_NAME}            # 중지"
echo "  pm2 restart ${APP_NAME}           # 재시작"
echo "  pm2 delete  ${APP_NAME}           # 완전 삭제"
echo "  pm2 monit                         # 대화형 모니터"
echo "=================================================="
