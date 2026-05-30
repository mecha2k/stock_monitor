import os
from typing import List

# 1. 대상 주식 티커 목록 (UPPER_SNAKE_CASE)
TARGET_STOCKS: List[str] = ["AAPL", "GOOGL", "TSLA"]

# 2. 텔레그램 봇 API 설정 (기본값 설정 및 환경 변수 연동)
# 실운영 시 환경 변수(Environment Variable)를 설정하시거나 아래 기본값 문자열을 실제 정보로 수정해 주세요.
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_HERE")

# 3. Gemini API 설정 (뉴스 요약 및 감성 분석을 위한 AI API 키)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# 4. 알림 시간 설정 (24시간 형식, KST 기준)
NOTIFICATION_TIME: str = "08:00"
