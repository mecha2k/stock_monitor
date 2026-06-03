"""
find_chat_id.py
===============
텔레그램 CHAT_ID 조회 유틸리티

[사용법]
1. .env 파일에 TELEGRAM_BOT_TOKEN을 먼저 입력하세요.
2. 이 스크립트를 실행하세요: python find_chat_id.py
3. 텔레그램에서 본인의 봇에게 아무 메시지나 전송하세요.
4. 콘솔에 출력되는 Chat ID를 .env 의 TELEGRAM_CHAT_ID에 붙여넣으세요.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_path, encoding="utf-8")
except ImportError:
    print("[경고] python-dotenv 미설치 — 시스템 환경 변수만 사용합니다.")

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 로깅 설정 (INFO 레벨로 텔레그램 라이브러리 로그 억제)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.WARNING,
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """수신된 모든 메시지에서 Chat ID를 출력합니다."""
    chat = update.effective_chat
    user = update.effective_user

    print("\n" + "=" * 50)
    print("✅  Chat ID를 찾았습니다!")
    print("=" * 50)
    print(f"  Chat ID   : {chat.id}")
    print(f"  Chat 유형  : {chat.type}")          # private / group / supergroup / channel
    print(f"  보낸 사람   : {user.full_name} (@{user.username})")
    print("=" * 50)
    print("\n👉 .env 파일에 아래 값을 붙여넣으세요:")
    print(f"   TELEGRAM_CHAT_ID={chat.id}\n")

    # 봇이 확인 메시지를 발신자에게 자동 회신
    await update.message.reply_text(
        f"✅ Chat ID 확인 완료!\n\n"
        f"📋 Chat ID: `{chat.id}`\n\n"
        f"이 값을 `.env` 파일의 `TELEGRAM_CHAT_ID`에 입력하세요.",
        parse_mode="Markdown",
    )

    # Chat ID 확인 후 봇 종료
    print("봇을 종료합니다. (Ctrl+C 로도 종료 가능)\n")
    asyncio.get_event_loop().stop()


def main() -> None:
    # TELEGRAM_BOT_TOKEN 유효성 검사
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "your_telegram_bot_token_here":
        print("[오류] .env 파일에 유효한 TELEGRAM_BOT_TOKEN이 없습니다.")
        print("       BotFather(https://t.me/BotFather)에서 토큰을 발급받아 입력하세요.")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("🤖  텔레그램 Chat ID 조회 봇 시작")
    print("=" * 50)
    print("  → 텔레그램에서 본인의 봇에게 아무 메시지나 보내세요.")
    print("  → Chat ID가 자동으로 출력됩니다.")
    print("  → 종료: Ctrl+C\n")

    # 봇 애플리케이션 빌드 및 핸들러 등록
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # Polling 방식으로 메시지 수신 대기
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
