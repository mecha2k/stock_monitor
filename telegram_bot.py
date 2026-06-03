"""
telegram_bot.py
===============
Telegram Bot API 전용 모듈 (python-telegram-bot v21+ 대응)

역할:
- python-telegram-bot 라이브러리를 활용한 고수준 메시지 발송 추상화
- 텍스트 메시지, HTML 포맷 메시지, 사진 첨부 등 다양한 전송 방식 지원
- 재시도(Retry) 로직 및 에러 핸들링 내장

사용 방법:
    from telegram_bot import TelegramNotifier

    notifier = TelegramNotifier()
    await notifier.send_message("안녕하세요! 📈")
"""

import os
import asyncio
import logging
import concurrent.futures
from typing import Optional
from pathlib import Path

# python-telegram-bot 라이브러리 임포트
try:
    from telegram import Bot, LinkPreviewOptions, error as telegram_error
    from telegram.constants import ParseMode
except ImportError as e:
    raise ImportError(
        "python-telegram-bot 라이브러리가 설치되어 있지 않습니다.\n"
        "다음 명령어로 설치해 주세요: pip install 'python-telegram-bot>=21.0'"
    ) from e

# .env 파일 자동 로드 (python-dotenv)
try:
    from dotenv import load_dotenv

    # 현재 파일 기준으로 .env 경로를 명시적으로 지정
    _env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_path, encoding="utf-8")
except ImportError:
    pass  # dotenv가 없어도 시스템 환경 변수로 동작 가능

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Telegram Bot API를 통한 알림 전송 전용 클래스입니다.

    python-telegram-bot v21+ 라이브러리의 Bot 객체를 래핑하여
    메시지 전송, 에러 핸들링, 토큰 유효성 검사 기능을 제공합니다.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        TelegramNotifier 초기화

        Args:
            bot_token (Optional[str]): 봇 토큰. None이면 환경 변수 TELEGRAM_BOT_TOKEN 사용.
            chat_id (Optional[str]): 채팅 ID. None이면 환경 변수 TELEGRAM_CHAT_ID 사용.

        Raises:
            ValueError: 토큰이나 채팅 ID가 설정되지 않거나 플레이스홀더인 경우
        """
        self.bot_token: str = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id: str = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

        # 설정값 유효성 검사
        self._validate_credentials()

        # Bot 인스턴스 초기화
        self._bot = Bot(token=self.bot_token)
        logger.info("TelegramNotifier 초기화 완료. Chat ID: %s", self.chat_id)

    def _validate_credentials(self) -> None:
        """
        환경 변수로부터 로드된 인증 정보의 유효성을 검사합니다.

        Raises:
            ValueError: 토큰 또는 채팅 ID가 비어있거나 기본 플레이스홀더 값인 경우
        """
        placeholder_values = {
            "YOUR_TELEGRAM_BOT_TOKEN_HERE",
            "YOUR_TELEGRAM_CHAT_ID_HERE",
        }

        if not self.bot_token or self.bot_token in placeholder_values:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.\n"
                ".env 파일 또는 환경 변수에 실제 봇 토큰을 입력해 주세요."
            )

        if not self.chat_id or self.chat_id in placeholder_values:
            raise ValueError(
                "TELEGRAM_CHAT_ID가 설정되지 않았습니다.\n"
                ".env 파일 또는 환경 변수에 실제 채팅 ID를 입력해 주세요."
            )

    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        disable_preview: bool = True,
    ) -> bool:
        """
        텍스트 메시지를 텔레그램 채팅으로 비동기 전송합니다.

        v22+ 변경사항: disable_web_page_preview → LinkPreviewOptions 사용

        Args:
            text (str): 전송할 메시지 내용 (HTML 태그 사용 가능)
            parse_mode (str): 파싱 모드. 기본값은 HTML.
            disable_preview (bool): URL 미리보기 비활성화 여부. 기본값 True.

        Returns:
            bool: 전송 성공이면 True, 실패이면 False
        """
        # v22+에서 deprecated된 disable_web_page_preview 대신 LinkPreviewOptions 사용
        link_preview = LinkPreviewOptions(is_disabled=disable_preview)

        try:
            await self._bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                link_preview_options=link_preview,
            )
            logger.info("텔레그램 메시지 전송 성공 (Chat ID: %s)", self.chat_id)
            return True

        except telegram_error.InvalidToken:
            logger.error(
                "잘못된 봇 토큰입니다. BotFather에서 발급받은 토큰을 확인해 주세요."
            )
        except telegram_error.ChatNotFound:
            logger.error(
                "Chat ID '%s'를 찾을 수 없습니다. "
                "봇이 해당 채팅에 초대되어 있는지 확인해 주세요.",
                self.chat_id,
            )
        except telegram_error.RetryAfter as e:
            logger.warning(
                "Telegram API 속도 제한(Rate Limit)으로 인해 %.1f초 후 재시도합니다.",
                e.retry_after,
            )
            await asyncio.sleep(e.retry_after)
            return await self.send_message(text, parse_mode, disable_preview)
        except telegram_error.NetworkError as e:
            logger.error("네트워크 오류로 전송 실패: %s", e)
        except Exception as e:
            logger.error("알 수 없는 오류로 전송 실패: %s", e)

        return False

    async def send_photo(
        self,
        photo_path: str,
        caption: Optional[str] = None,
    ) -> bool:
        """
        로컬 이미지 파일을 텔레그램으로 전송합니다.

        Args:
            photo_path (str): 전송할 이미지 파일의 로컬 경로
            caption (Optional[str]): 이미지 하단에 표시할 캡션 (HTML 지원)

        Returns:
            bool: 전송 성공이면 True, 실패이면 False
        """
        path = Path(photo_path)
        if not path.exists():
            logger.error("이미지 파일을 찾을 수 없습니다: %s", photo_path)
            return False

        try:
            with open(path, "rb") as photo_file:
                await self._bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML if caption else None,
                )
            logger.info("텔레그램 이미지 전송 성공: %s", path.name)
            return True

        except Exception as e:
            logger.error("이미지 전송 실패: %s", e)
            return False

    async def verify_connection(self) -> bool:
        """
        봇 토큰의 유효성과 API 연결 상태를 사전 검증합니다.

        Returns:
            bool: 연결이 정상이면 True, 실패이면 False
        """
        try:
            bot_info = await self._bot.get_me()
            logger.info(
                "봇 연결 확인 완료. 봇 이름: @%s (ID: %d)",
                bot_info.username,
                bot_info.id,
            )
            return True
        except telegram_error.InvalidToken:
            logger.error("유효하지 않은 봇 토큰입니다.")
        except Exception as e:
            logger.error("봇 연결 검증 실패: %s", e)
        return False

    def send_message_sync(self, text: str, **kwargs) -> bool:
        """
        동기(Sync) 환경에서 메시지를 전송하는 래퍼 메서드입니다.
        기존 동기 코드(stock_agent.py 등)에서 호출할 때 사용합니다.

        이벤트 루프 충돌을 방지하기 위해 별도 스레드에서 실행합니다.

        Args:
            text (str): 전송할 메시지 내용
            **kwargs: send_message()에 전달할 추가 인자

        Returns:
            bool: 전송 성공이면 True, 실패이면 False
        """

        def _run_in_thread() -> bool:
            """별도 스레드에서 새로운 이벤트 루프를 생성하여 실행합니다."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.send_message(text, **kwargs)
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_thread)
            return future.result()


# ──────────────────────────────────────────────
# 모듈 단독 실행 시 연결 테스트 수행
# ──────────────────────────────────────────────
async def _run_connection_test() -> None:
    """봇 연결 및 테스트 메시지 전송을 검증하는 비동기 함수입니다."""
    print("=" * 50)
    print("  Telegram Bot 연결 테스트")
    print("=" * 50)

    try:
        notifier = TelegramNotifier()

        # 1단계: 봇 토큰 유효성 검사
        print("\n[1단계] 봇 연결 상태 확인 중...")
        is_connected = await notifier.verify_connection()
        if not is_connected:
            print(
                "❌ 연결 실패. .env 파일의 TELEGRAM_BOT_TOKEN을 확인해 주세요."
            )
            return

        # 2단계: 테스트 메시지 전송
        print("\n[2단계] 테스트 메시지 전송 중...")
        test_message = (
            "<b>🤖 Stock Monitor Bot - 연결 테스트</b>\n\n"
            "✅ 텔레그램 봇이 정상적으로 설정되었습니다!\n"
            "이제 주식 모니터링 알림을 수신할 준비가 완료되었습니다. 📈"
        )
        success = await notifier.send_message(test_message)

        if success:
            print("\n✅ 테스트 완료! 텔레그램에서 메시지를 확인해 주세요.")
        else:
            print("\n❌ 메시지 전송 실패. 로그를 확인해 주세요.")

    except ValueError as e:
        print(f"\n⚠️  설정 오류: {e}")


if __name__ == "__main__":
    asyncio.run(_run_connection_test())
