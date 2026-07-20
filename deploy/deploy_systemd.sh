#!/usr/bin/env bash
# ============================================================
# deploy_systemd.sh
# 우분투 서버에 stock-scheduler를 Systemd 서비스로 등록합니다.
#
# 사용법:
#   1. 아래 변수 3개를 실제 환경에 맞게 수정하세요.
#   2. chmod +x deploy_systemd.sh && sudo ./deploy_systemd.sh
# ============================================================

set -euo pipefail

# ──────────────────────────────────────────────────────────
# ✏️  실제 환경에 맞게 수정하세요
# ──────────────────────────────────────────────────────────
SERVICE_USER="ubuntu"
PROJECT_DIR="/home/ubuntu/codes/antigravity/stock_monitor"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
# ──────────────────────────────────────────────────────────

SERVICE_NAME="stock-scheduler"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=================================================="
echo "  Stock Monitor — Systemd 서비스 등록 시작"
echo "=================================================="

# 1. 서비스 파일 생성
echo "[1/5] 서비스 파일 작성: ${SERVICE_FILE}"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Stock Monitor Scheduler — 미국 주식 일일 모니터링 서비스
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${VENV_PYTHON} scheduler.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. 권한 설정
chmod 644 "${SERVICE_FILE}"

# 3. systemd 데몬 재로드
echo "[2/5] systemd 데몬 재로드..."
systemctl daemon-reload

# 4. 부팅 시 자동 시작 활성화
echo "[3/5] 부팅 자동 시작 활성화..."
systemctl enable "${SERVICE_NAME}"

# 5. 서비스 즉시 시작
echo "[4/5] 서비스 시작..."
systemctl start "${SERVICE_NAME}"

# 6. 상태 확인
echo "[5/5] 서비스 상태 확인..."
sleep 2
systemctl status "${SERVICE_NAME}" --no-pager

echo ""
echo "=================================================="
echo "  ✅ 등록 완료!"
echo ""
echo "  📋 유용한 관리 명령어:"
echo "  sudo systemctl status ${SERVICE_NAME}    # 상태 확인"
echo "  sudo systemctl stop   ${SERVICE_NAME}    # 중지"
echo "  sudo systemctl restart ${SERVICE_NAME}   # 재시작"
echo "  sudo journalctl -u ${SERVICE_NAME} -f    # 실시간 로그"
echo "=================================================="
