#!/usr/bin/env bash
# ============================================================
# setup_server.sh
# 우분투 서버 최초 1회 환경 설정 스크립트
# Python 가상환경 생성 및 의존성 패키지 설치
#
# 사용법:
#   1. 소스코드를 서버에 업로드한 뒤 이 스크립트를 실행하세요.
#   2. chmod +x setup_server.sh && ./setup_server.sh
# ============================================================

set -euo pipefail

# ──────────────────────────────────────────────────────────
# ✏️  실제 환경에 맞게 수정하세요
# ──────────────────────────────────────────────────────────
PROJECT_DIR="/home/ubuntu/stock_monitor"
# ──────────────────────────────────────────────────────────

echo "=================================================="
echo "  Stock Monitor — 서버 초기 환경 설정"
echo "=================================================="

# 1. Python 3 및 uv 설치 확인
echo "[1/5] Python 3 및 uv 확인..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip curl

if ! command -v uv &> /dev/null; then
    echo "  → uv가 존재하지 않아 설치를 시작합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # PATH에 uv 추가
    export PATH="${HOME}/.local/bin:${PATH}"
fi

PYTHON_VER=$(python3 --version)
UV_VER=$(uv --version)
echo "  → ${PYTHON_VER} / ${UV_VER} 설치 확인"

# 2. 프로젝트 디렉터리 이동
cd "${PROJECT_DIR}"
echo "[2/5] 프로젝트 디렉터리: ${PROJECT_DIR}"

# 3. 가상환경 생성
echo "[3/5] 가상환경(.venv) 생성..."
if [ ! -d ".venv" ]; then
    uv venv .venv
    echo "  → .venv 생성 완료 (uv)"
else
    echo "  → .venv 이미 존재, 건너뜁니다."
fi

# 4. 패키지 설치
echo "[4/5] 의존성 패키지 설치 (requirements.txt)..."
uv pip install -r requirements.txt -q
echo "  → 설치 완료"

# 5. .env 파일 존재 여부 확인
echo "[5/5] .env 파일 확인..."
if [ ! -f ".env" ]; then
    echo "  ⚠️  .env 파일이 없습니다."
    echo "  아래 내용으로 .env 파일을 생성하고 값을 입력하세요:"
    echo ""
    echo "  cat > ${PROJECT_DIR}/.env <<EOF"
    echo "  TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here"
    echo "  TELEGRAM_CHAT_ID=your_telegram_chat_id_here"
    echo "  GEMINI_API_KEY=your_gemini_api_key_here"
    echo "  EOF"
else
    echo "  → .env 파일 확인 완료"
fi

echo ""
echo "=================================================="
echo "  ✅ 초기 설정 완료!"
echo ""
echo "  다음 단계:"
echo "  1. .env 파일에 API 키를 입력하세요."
echo "  2. 아래 배포 스크립트 중 하나를 선택해 실행하세요:"
echo "     sudo ./deploy/deploy_systemd.sh   ← 권장 (운영 환경)"
echo "          ./deploy/deploy_pm2.sh       ← 편리한 모니터링"
echo "          ./deploy/deploy_nohup.sh     ← 즉시 실행 (임시)"
echo "=================================================="
