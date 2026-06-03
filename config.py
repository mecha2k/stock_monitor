"""
config.py
=========
애플리케이션 전역 설정 관리 모듈

.env 파일 또는 시스템 환경 변수에서 민감 정보를 로드하여
다른 모듈에서 안전하게 참조할 수 있도록 중앙화합니다.

우선순위: 시스템 환경 변수 > .env 파일 > 코드 내 기본값
"""

import os
from typing import List
from pathlib import Path

# python-dotenv를 통해 프로젝트 루트의 .env 파일을 자동 로드합니다.
# 시스템 환경 변수가 이미 설정된 경우, .env의 값은 override하지 않습니다.
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_path, encoding="utf-8", override=False)
except ImportError:
    # python-dotenv 미설치 시 시스템 환경 변수만 사용
    pass

# ──────────────────────────────────────────────
# 1. 모니터링 대상 주식 티커 목록
# ──────────────────────────────────────────────
TARGET_STOCKS: List[str] = ["AAPL", "GOOGL", "TSLA"]

# ──────────────────────────────────────────────
# 2. Telegram Bot API 설정
#    .env 파일 또는 환경 변수에서 자동 로드됩니다.
# ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_HERE")

# ──────────────────────────────────────────────
# 3. Google Gemini API 설정
#    뉴스 요약 및 감성 분석을 위한 AI API 키
# ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# ──────────────────────────────────────────────
# 4. 알림 발송 시각 (KST 기준, 24시간 형식)
# ──────────────────────────────────────────────
NOTIFICATION_TIME: str = "08:00"
