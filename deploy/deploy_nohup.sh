#!/usr/bin/env bash
# ============================================================
# deploy_nohup.sh
# nohup을 사용하여 stock-scheduler를 즉시 백그라운드로 실행합니다.
# 추가 설치 없이 사용 가능한 가장 간단한 방법입니다.
#
# 사용법:
#   1. 아래 변수를 실제 환경에 맞게 수정하세요.
#   2. chmod +x deploy_nohup.sh && ./deploy_nohup.sh
# ============================================================

set -euo pipefail

# ──────────────────────────────────────────────────────────
# ✏️  실제 환경에 맞게 수정하세요
# ──────────────────────────────────────────────────────────
PROJECT_DIR="/home/ubuntu/stock_monitor"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
LOG_FILE="${PROJECT_DIR}/scheduler.log"
PID_FILE="${PROJECT_DIR}/scheduler.pid"
# ──────────────────────────────────────────────────────────

echo "=================================================="
echo "  Stock Monitor — nohup 백그라운드 실행 시작"
echo "=================================================="

# 기존에 실행 중인 프로세스가 있으면 종료
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "[사전 정리] 기존 프로세스(PID: ${OLD_PID}) 종료..."
        kill "${OLD_PID}"
        sleep 1
    fi
    rm -f "${PID_FILE}"
fi

# nohup으로 백그라운드 실행
echo "[1/2] 스케줄러를 백그라운드로 실행..."
cd "${PROJECT_DIR}"
nohup "${VENV_PYTHON}" scheduler.py \
    >> "${LOG_FILE}" 2>&1 &

# PID 저장
SCHEDULER_PID=$!
echo "${SCHEDULER_PID}" > "${PID_FILE}"

sleep 1

# 정상 실행 여부 확인
if kill -0 "${SCHEDULER_PID}" 2>/dev/null; then
    echo "[2/2] 실행 확인 완료!"
    echo ""
    echo "=================================================="
    echo "  ✅ 정상 실행 중!"
    echo "  PID  : ${SCHEDULER_PID}  (파일: ${PID_FILE})"
    echo "  로그  : ${LOG_FILE}"
    echo ""
    echo "  📋 유용한 관리 명령어:"
    echo "  tail -f ${LOG_FILE}           # 실시간 로그 확인"
    echo "  kill \$(cat ${PID_FILE})      # 프로세스 종료"
    echo "  ps aux | grep scheduler.py    # 실행 상태 확인"
    echo "=================================================="
else
    echo "❌ 프로세스 시작 실패. 로그를 확인하세요:"
    echo "  cat ${LOG_FILE}"
    exit 1
fi
