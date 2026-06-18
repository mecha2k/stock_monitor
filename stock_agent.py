import os
import time
import sys
import json
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import urllib.request
import urllib.parse
import config

# Windows CP949 터미널 인코딩 오류 방지 (print 시 이모지 깨짐 현상 예방)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 1. 한국 표준시 (KST) 타임존 설정
KST = timezone(timedelta(hours=9))


class StockAgent:
    """미국 주식 뉴스를 모니터링하고 분석하여 텔레그램으로 전송하는 핵심 에이전트 클래스입니다."""

    # 1차 모델: 최신 고성능 모델 / 2차 모델: 1차 실패 시 폴백 모델
    PRIMARY_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-2.5-flash-lite"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self) -> None:
        """StockAgent 클래스의 생성자입니다."""
        # config.TARGET_STOCKS가 딕셔너리 리스트로 변경됨
        self.stock_configs: List[Dict[str, Any]] = config.TARGET_STOCKS
        self.bot_token: str = config.TELEGRAM_BOT_TOKEN
        self.chat_id: str = config.TELEGRAM_CHAT_ID
        self.gemini_key: str = config.GEMINI_API_KEY
        self.alpha_vantage_key: str = getattr(config, "ALPHA_VANTAGE_API_KEY", "")

    def normalize_text(self, text: str) -> str:
        """
        한글 자소 깨짐(NFC/NFD)을 방지하기 위해 유니코드 정규화를 처리합니다.

        Args:
            text (str): 정규화할 원본 텍스트

        Returns:
            str: NFC 표준 정규화된 텍스트
        """
        if not text:
            return ""
        return unicodedata.normalize("NFC", text)

    def fetch_stock_price(self, ticker: str) -> Optional[float]:
        """
        yfinance를 사용하여 해당 티커의 전일 종가(Close Price)를 조회합니다.
        장 마감 전에 실행될 경우 당일 가장 최근 가격을 반환합니다.

        Args:
            ticker (str): 주식 티커 (예: "AAPL")

        Returns:
            Optional[float]: 종가(USD). 조회 실패 시 None 반환
        """
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            # 최근 2일치 일봉 데이터를 가져와 가장 최근 종가 반환
            hist = stock.history(period="2d")
            if hist.empty:
                print(f"[{ticker}] 종가 데이터가 없습니다.")
                return None

            close_price = float(hist["Close"].iloc[-1])
            print(f"[{ticker}] 최근 종가: ${close_price:.2f}")
            return close_price

        except ImportError:
            print(
                f"[{ticker}] yfinance 미설치 — 종가 수집을 건너뜁니다. "
                "(설치: uv pip install yfinance)"
            )
            return None
        except Exception as e:
            print(f"[{ticker}] 종가 수집 실패: {e}")
            return None

    def fetch_alphavantage_news(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Alpha Vantage API를 통해 특정 주식 티커의 최신 뉴스를 수집합니다.

        Args:
            ticker (str): 주식 티커 (예: "AAPL")

        Returns:
            List[Dict[str, Any]]: 수집된 최신 뉴스 목록 (최대 3개)
        """
        if not self.alpha_vantage_key or "YOUR_ALPHAVANTAGE_API_KEY_HERE" in self.alpha_vantage_key:
            print(f"[{ticker}] Alpha Vantage API 키가 없어 뉴스 수집을 건너뜁니다.")
            return []

        # limit=3 파라미터로 최신 3개만 요청
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit=3&apikey={self.alpha_vantage_key}"
        print(f"[{ticker}] Alpha Vantage 뉴스 수집 중...")

        try:
            # 403 Forbidden 등 방화벽 차단을 우회하기 위해 User-Agent 명시
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))

            news_list: List[Dict[str, Any]] = []
            feed = res_data.get("feed", [])

            for entry in feed[:3]:
                news_list.append(
                    {
                        "title": entry.get("title", "제목 없음"),
                        "link": entry.get("url", "#"),
                        "published": entry.get("time_published", "시간 정보 없음"),
                        "summary_source": entry.get("summary", ""),
                    }
                )
            return news_list
        except urllib.error.HTTPError as e:
            print(f"[{ticker}] Alpha Vantage API 호출 실패 (HTTP {e.code}): {e.read().decode('utf-8', errors='replace')}")
            return []
        except Exception as e:
            print(f"[{ticker}] Alpha Vantage 뉴스 수집 실패: {e}")
            return []

    def _call_gemini_with_retry(
        self, ticker: str, model: str, payload: dict, max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        지정된 모델로 Gemini API를 호출하고, 429 발생 시 Exponential Backoff로 재시도합니다.
        성공 시 파싱된 딕셔너리를 반환하고, 모든 재시도 실패 시 None을 반환합니다.

        Args:
            ticker (str): 로그 출력용 주식 티커
            model (str): 호출할 Gemini 모델명
            payload (dict): API 요청 본문
            max_retries (int): 최대 재시도 횟수 (기본 3회)

        Returns:
            Optional[Dict[str, Any]]: 성공 시 분석 결과 딕셔너리, 실패 시 None
        """
        url = f"{self.GEMINI_BASE_URL}/{model}:generateContent?key={self.gemini_key}"

        for attempt in range(1, max_retries + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url, data=data, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    response_text = (
                        res_body.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    ).strip()

                    # Gemini가 ```json ... ``` 마크다운 블록으로 응답할 경우 제거
                    if response_text.startswith("```"):
                        lines = response_text.splitlines()
                        response_text = "\n".join(lines[1:-1]).strip()

                    result = json.loads(response_text)
                    result["summary"] = self.normalize_text(
                        result.get("summary", "요약 생성 실패")
                    )
                    result["sentiment"] = self.normalize_text(
                        result.get("sentiment", "중립")
                    )
                    print(f"[{ticker}] [{model}] 분석 성공.")
                    return result

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                try:
                    err_msg = (
                        json.loads(err_body)
                        .get("error", {})
                        .get("message", err_body[:200])
                    )
                except json.JSONDecodeError:
                    err_msg = err_body[:200]

                if e.code == 429:
                    wait_sec = 8 * (2 ** (attempt - 1))
                    is_last = attempt == max_retries
                    if is_last:
                        # 마지막 시도 실패: 추가 대기 없이 None 반환
                        print(
                            f"[{ticker}] [{model}] 429 Rate Limit — "
                            f"최대 재시도({max_retries}회) 소진. 다음 모델로 전환합니다."
                        )
                    else:
                        print(
                            f"[{ticker}] [{model}] 429 Rate Limit "
                            f"(시도 {attempt}/{max_retries}). {wait_sec}초 대기 후 재시도합니다."
                        )
                        time.sleep(wait_sec)
                else:
                    # 401, 400 등 재시도해도 해결되지 않는 오류는 즉시 중단
                    print(
                        f"[{ticker}] [{model}] HTTP {e.code} 오류 (재시도 불필요): {err_msg}"
                    )
                    return None

            except Exception as e:
                print(f"[{ticker}] [{model}] 예외 발생: {e}")
                return None

        return None

    def analyze_news_with_gemini(self, ticker: str, title: str, summary_source: str = "") -> Dict[str, Any]:
        """
        Gemini LLM API를 호출하여 뉴스의 주가 영향도 감성 분석 및 핵심 요약을 생성합니다.
        1차 모델(gemini-2.5-flash) 실패 시 2차 모델(gemini-2.0-flash-lite)로 자동 폴백합니다.
        두 모델 모두 실패 시 로컬 Mock 분석 엔진으로 대체합니다.

        Args:
            ticker (str): 주식 티커
            title (str): 영문 뉴스 제목
            summary_source (str): Finnhub 등에서 제공받은 영문 뉴스 요약문 (선택 사항)

        Returns:
            Dict[str, Any]: 감성 분석 결과 및 요약 딕셔너리
        """
        # API 키가 비어있거나 플레이스홀더인 경우 Mock 처리
        if not self.gemini_key or "YOUR_GEMINI_API_KEY" in self.gemini_key:
            print(
                f"[{ticker}] Gemini API 키 미설정 — Mock 가상 분석 모드로 수행합니다."
            )
            return self._mock_analysis(ticker, title)

        prompt = (
            f"주식 티커: {ticker}\n"
            f"뉴스 제목: {title}\n"
            f"뉴스 원문 요약: {summary_source}\n\n"
            "위의 영문 뉴스가 해당 주가에 미칠 단기적 영향을 분석하고 반드시 한국어로만 대답해주세요.\n"
            "JSON 형식:\n"
            "{\n"
            '  "sentiment": "긍정적/부정적/중립 중 하나",\n'
            '  "impact_score": 0~100 사이 정수,\n'
            '  "summary": "한국어로 번역 요약한 내용 (3문장 이내)"\n'
            "}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        # ── 1차 시도: PRIMARY_MODEL (gemini-2.5-flash) ──────────────────────
        result = self._call_gemini_with_retry(ticker, self.PRIMARY_MODEL, payload)
        if result is not None:
            return result

        # ── 2차 시도: FALLBACK_MODEL (gemini-2.0-flash-lite) ────────────────
        print(f"[{ticker}] {self.FALLBACK_MODEL} 폴백 모델로 재시도합니다.")
        result = self._call_gemini_with_retry(ticker, self.FALLBACK_MODEL, payload)
        if result is not None:
            return result

        # ── 3차 최종 폴백: 로컬 Mock 분석 엔진 ─────────────────────────────
        print(f"[{ticker}] 모든 Gemini 모델 호출 실패 — 로컬 Mock 분석으로 대체합니다.")
        return self._mock_analysis(ticker, title)

    def _mock_analysis(self, ticker: str, title: str) -> Dict[str, Any]:
        """
        API 호출에 실패하거나 키가 없을 시 사용하는 로컬 폴백 모의 분석기입니다.

        Args:
            ticker (str): 주식 티커
            title (str): 뉴스 제목

        Returns:
            Dict[str, Any]: 가상의 분석 정보
        """
        title_lower = title.lower()
        if any(
            w in title_lower
            for w in ["rise", "surge", "up", "growth", "win", "beat", "new"]
        ):
            sentiment = "긍정적"
            score = 75
            summary = (
                f"해당 뉴스는 {ticker} 관련 호재성 뉴스로 보이며"
                " 기술 성장 또는 호조세 소식을 담고 있습니다."
            )
        elif any(
            w in title_lower
            for w in ["fall", "drop", "down", "loss", "fail", "investigation"]
        ):
            sentiment = "부정적"
            score = 25
            summary = (
                f"해당 뉴스는 {ticker} 관련 악재성 뉴스일 가능성이 있으며"
                " 하락 또는 리스크 요인을 언급하고 있습니다."
            )
        else:
            sentiment = "중립"
            score = 50
            summary = (
                f"해당 뉴스는 {ticker}에 대해 시장에 큰 영향을 미치지 않는"
                " 일반적 동향 뉴스입니다."
            )

        return {
            "sentiment": self.normalize_text(sentiment),
            "impact_score": score,
            "summary": self.normalize_text(summary),
        }

    def send_telegram_message(self, message: str) -> bool:
        """
        텔레그램 API를 사용하여 수집 및 분석 리포트를 대상 채널로 전송합니다.

        Args:
            message (str): 전송할 HTML 서식의 메시지

        Returns:
            bool: 전송 성공 여부
        """
        if not self.bot_token or "YOUR_TELEGRAM_BOT_TOKEN" in self.bot_token:
            print(
                "텔레그램 봇 토큰이 올바르게 설정되지 않아 알림 발송을 취소하고 콘솔에 출력합니다."
            )
            print(message)
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                if res.get("ok"):
                    print("텔레그램 알림 발송에 성공했습니다.")
                    return True
                else:
                    print(f"텔레그램 응답 실패: {res}")
                    return False
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return False

    def build_report_message(self, all_analyses: Dict[str, Dict[str, Any]]) -> str:
        """
        티커별 최고 점수 뉴스 1개씩 선별된 분석 결과와
        종가 / 매수·매도 희망가 비교 정보를 텔레그램 친화적인 HTML 형식으로 구성합니다.

        Args:
            all_analyses: 티커별 분석 및 가격 정보 딕셔너리

        Returns:
            str: HTML 포맷팅된 최종 메시지
        """
        current_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

        msg_lines = [
            f"<b>🔔 미국 주식 일일 모니터링 리포트</b>",
            f"📅 <i>발송 일시: {current_time_str}</i>",
            f"=======================\n",
        ]

        for ticker, item in all_analyses.items():
            msg_lines.append(f"<b>📈 {ticker}</b>")

            # ── 종가 / 매수·매도 희망가 섹션 ─────────────────────────────
            close_price: Optional[float] = item.get("close_price")
            buy_price: float = item.get("buy_price", 0.0)
            sell_price: float = item.get("sell_price", 0.0)

            if close_price is not None:
                msg_lines.append(f"💰 종가: <b>${close_price:,.2f}</b>")

                # 희망가 정보 한 줄 출력
                target_parts = []
                if buy_price > 0:
                    buy_str = f"{buy_price:,.0f}" if buy_price.is_integer() else f"{buy_price:,.2f}"
                    target_parts.append(f"🛒 매수 (${buy_str})")
                if sell_price > 0:
                    sell_str = f"{sell_price:,.0f}" if sell_price.is_integer() else f"{sell_price:,.2f}"
                    target_parts.append(f"📈 매도 (${sell_str})")
                if target_parts:
                    msg_lines.append(f"희망가 : {', '.join(target_parts)}")

                # 매수 희망가 도달 체크 (희망가 +5% 이하)
                if buy_price > 0 and close_price <= buy_price * 1.05:
                    msg_lines.append(
                        "🎯🔥 <b>매수 희망가 도달! 지금이 매수 타이밍입니다!</b>"
                    )

                # 매도 희망가 도달 체크 (희망가 -5% 이상)
                if sell_price > 0 and close_price >= sell_price * 0.95:
                    msg_lines.append(
                        "🚀💰 <b>매도 희망가 도달! 지금이 매도 타이밍입니다!</b>"
                    )

            else:
                msg_lines.append("💰 종가: <i>수집 실패</i>")
                target_parts = []
                if buy_price > 0:
                    buy_str = f"{buy_price:,.0f}" if buy_price.is_integer() else f"{buy_price:,.2f}"
                    target_parts.append(f"🛒 매수 (${buy_str})")
                if sell_price > 0:
                    sell_str = f"{sell_price:,.0f}" if sell_price.is_integer() else f"{sell_price:,.2f}"
                    target_parts.append(f"📈 매도 (${sell_str})")
                if target_parts:
                    msg_lines.append(f"희망가 : {', '.join(target_parts)}")

            msg_lines.append("")

            # ── 뉴스 분석 섹션 ────────────────────────────────────────────
            if not item.get("title"):
                msg_lines.append("📰 수집된 뉴스가 없습니다.\n")
            else:
                sentiment_emoji = (
                    "🟢"
                    if "긍정" in item["sentiment"]
                    else ("🔴" if "부정" in item["sentiment"] else "⚪")
                )
                msg_lines.append(
                    f"📰 <b><a href='{item['link']}'>{item['title']}</a></b>"
                )
                msg_lines.append(
                    f"└ {sentiment_emoji} 영향도: "
                    f"<b>{item['sentiment']}</b> "
                    f"(점수: <b>{item['impact_score']}</b>/100)"
                )
                msg_lines.append(f"└ 요약: {item['summary']}\n")

            msg_lines.append("-----------------------")

        return "\n".join(msg_lines)

    def run_daily_workflow(self) -> None:
        """일일 전체 뉴스 수집, 종가 조회, 매수/매도 희망가 비교, LLM 분석,
        최고 점수 1개 선별 후 텔레그램 전송 워크플로우를 작동시킵니다."""
        print("💡 [StockAgent] 일일 주식 모니터링 워크플로우 시작...")

        # 티커별 최고 점수 뉴스 단일 항목 + 가격 정보를 저장
        all_analyses: Dict[str, Dict[str, Any]] = {}

        for stock_cfg in self.stock_configs:
            ticker: str = stock_cfg["ticker"]
            buy_price: float = stock_cfg.get("buy_price", 0.0)
            sell_price: float = stock_cfg.get("sell_price", 0.0)

            price_info = []
            if buy_price > 0:
                price_info.append(f"매수 ${buy_price:,.2f}")
            if sell_price > 0:
                price_info.append(f"매도 ${sell_price:,.2f}")
            price_desc = "  /  ".join(price_info) if price_info else "희망가 미설정"
            print(f"\n── [{ticker}] 처리 시작 ({price_desc}) ──")

            # 1) 종가 수집
            close_price = self.fetch_stock_price(ticker)

            # 2) 뉴스 수집 및 분석
            news_items = self.fetch_alphavantage_news(ticker)
            ticker_analyses: List[Dict[str, Any]] = []

            for news in news_items:
                analysis = self.analyze_news_with_gemini(ticker, news["title"], news.get("summary_source", ""))
                analysis["link"] = news["link"]
                analysis["title"] = self.normalize_text(news["title"])
                ticker_analyses.append(analysis)
                time.sleep(1)

            # 3) impact_score 최고 뉴스 1개 선별
            if ticker_analyses:
                top = max(ticker_analyses, key=lambda x: x.get("impact_score", 0))
                print(
                    f"[{ticker}] 최고 점수 뉴스 선별: "
                    f"'{top['title'][:40]}...' "
                    f"(점수: {top['impact_score']}/100)"
                )
                top["close_price"] = close_price
                top["buy_price"] = buy_price
                top["sell_price"] = sell_price
                all_analyses[ticker] = top
            else:
                all_analyses[ticker] = {
                    "close_price": close_price,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                }

            # 희망가 도달 여부 콘솔 출력
            if close_price is not None:
                if buy_price > 0:
                    if close_price <= buy_price * 1.05:
                        print(f"[{ticker}] 🎯🔥 매수 희망가 도달! ")
                    else:
                        print(f"[{ticker}] ⏳ 매수 희망가 미달성. ")
                if sell_price > 0:
                    if close_price >= sell_price * 0.95:
                        print(f"[{ticker}] 🚀💰 매도 희망가 도달! ")
                    else:
                        print(f"[{ticker}] ⏳ 매도 희망가 미달성. ")

        report = self.build_report_message(all_analyses)
        self.send_telegram_message(report)
        print("\n💡 [StockAgent] 워크플로우 완료.")


# 로컬 테스트용
if __name__ == "__main__":
    agent = StockAgent()
    agent.run_daily_workflow()
