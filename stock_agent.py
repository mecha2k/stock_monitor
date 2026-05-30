import os
import json
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import urllib.request
import urllib.parse
import feedparser
import config

# 1. 한국 표준시 (KST) 타임존 설정
KST = timezone(timedelta(hours=9))

class StockAgent:
    """미국 주식 뉴스를 모니터링하고 분석하여 텔레그램으로 전송하는 핵심 에이전트 클래스입니다."""
    
    def __init__(self) -> None:
        """StockAgent 클래스의 생성자입니다."""
        self.tickers: List[str] = config.TARGET_STOCKS
        self.bot_token: str = config.TELEGRAM_BOT_TOKEN
        self.chat_id: str = config.TELEGRAM_CHAT_ID
        self.gemini_key: str = config.GEMINI_API_KEY

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

    def fetch_rss_news(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Yahoo Finance RSS 피드를 통해 특정 주식 티커의 최신 뉴스를 수집합니다.
        
        Args:
            ticker (str): 주식 티커 (예: "AAPL")
            
        Returns:
            List[Dict[str, Any]]: 수집된 최신 뉴스 목록 (최대 3개)
        """
        rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        print(f"[{ticker}] RSS 피드 수집 중: {rss_url}")
        
        try:
            feed = feedparser.parse(rss_url)
            news_list: List[Dict[str, Any]] = []
            
            # 최신 뉴스 최대 3개만 추출
            for entry in feed.entries[:3]:
                news_list.append({
                    "title": entry.get("title", "제목 없음"),
                    "link": entry.get("link", "#"),
                    "published": entry.get("published", "시간 정보 없음")
                })
            return news_list
        except Exception as e:
            print(f"[{ticker}] 뉴스 수집 실패: {e}")
            return []

    def analyze_news_with_gemini(self, ticker: str, title: str) -> Dict[str, Any]:
        """
        Gemini LLM API를 호출하여 뉴스의 주가 영향도 감성 분석 및 핵심 요약을 생성합니다.
        API Key가 없거나 오류 시 Mock 분석 엔진으로 대체합니다.
        
        Args:
            ticker (str): 주식 티커
            title (str): 영문 뉴스 제목
            
        Returns:
            Dict[str, Any]: 감성 분석 결과 및 요약 딕셔너리
        """
        # API 키가 비어있거나 플레이스홀더인 경우 Mock 처리
        if not self.gemini_key or "YOUR_GEMINI_API_KEY" in self.gemini_key:
            print(f"[{ticker}] Gemini API 키가 감지되지 않아 Mock 가상 분석 모드로 수행합니다.")
            return self._mock_analysis(ticker, title)
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        
        prompt = (
            f"주식 티커: {ticker}\n"
            f"뉴스 제목: {title}\n\n"
            "위의 영문 뉴스가 해당 주가에 미칠 단기적 영향을 분석하고 반드시 아래의 JSON 형식으로만 한국어로 대답해주세요.\n"
            "JSON 형식:\n"
            "{\n"
            '  "sentiment": "긍정적/부정적/중립 중 하나",\n'
            '  "impact_score": 0~100 사이 정수,\n'
            '  "summary": "한국어로 번역 요약한 내용 (3문장 이내)"\n'
            "}"
        )
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                response_text = res_body["candidates"][0]["content"]["parts"][0]["text"].strip()
                result = json.loads(response_text)
                
                # 유니코드 정규화 수행
                result["summary"] = self.normalize_text(result.get("summary", "요약 생성 실패"))
                result["sentiment"] = self.normalize_text(result.get("sentiment", "중립"))
                return result
        except Exception as e:
            print(f"[{ticker}] Gemini API 호출 실패로 인해 Mock 분석으로 대체합니다. 에러: {e}")
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
        if any(w in title_lower for w in ["rise", "surge", "up", "growth", "win", "beat", "new"]):
            sentiment = "긍정적"
            score = 75
            summary = f"해당 뉴스는 {ticker} 관련 호재성 뉴스로 보이며 기술 성장 또는 호조세 소식을 담고 있습니다."
        elif any(w in title_lower for w in ["fall", "drop", "down", "loss", "fail", "investigation"]):
            sentiment = "부정적"
            score = 25
            summary = f"해당 뉴스는 {ticker} 관련 악재성 뉴스일 가능성이 있으며 하락 또는 리스크 요인을 언급하고 있습니다."
        else:
            sentiment = "중립"
            score = 50
            summary = f"해당 뉴스는 {ticker}에 대해 시장에 큰 영향을 미치지 않는 일반적 동향 뉴스입니다."
            
        return {
            "sentiment": self.normalize_text(sentiment),
            "impact_score": score,
            "summary": self.normalize_text(summary)
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
            print("텔레그램 봇 토큰이 올바르게 설정되지 않아 알림 발송을 취소하고 콘솔에 출력합니다.")
            print(message)
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
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

    def build_report_message(self, all_analyses: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        수집된 분석 결과를 텔레그램 친화적인 HTML 형식으로 구성합니다.
        
        Args:
            all_analyses (Dict[str, List[Dict[str, Any]]]): 티커별 분석 데이터 리스트
            
        Returns:
            str: HTML 포맷팅된 최종 메시지
        """
        current_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
        
        msg_lines = [
            f"<b>🔔 미국 주식 일일 모니터링 리포트</b>",
            f"📅 <i>발송 일시: {current_time_str}</i>",
            f"=======================\n"
        ]
        
        for ticker, analyses in all_analyses.items():
            msg_lines.append(f"<b>📈 {ticker} 분석 결과</b>")
            if not analyses:
                msg_lines.append("수집된 뉴스가 없습니다.\n")
                continue
                
            for idx, item in enumerate(analyses, 1):
                sentiment_emoji = "🟢" if "긍정" in item["sentiment"] else ("🔴" if "부정" in item["sentiment"] else "⚪")
                
                msg_lines.append(f"<b>{idx}. <a href='{item['link']}'>{item['title']}</a></b>")
                msg_lines.append(f"└ {sentiment_emoji} 영향도: <b>{item['sentiment']}</b> (점수: <b>{item['impact_score']}</b>/100)")
                msg_lines.append(f"└ 요약: {item['summary']}\n")
            msg_lines.append("-----------------------")
            
        return "\n".join(msg_lines)

    def run_daily_workflow(self) -> None:
        """일일 전체 뉴스 수집, LLM 분석, 텔레그램 전송 워크플로우를 작동시킵니다."""
        print("💡 [StockAgent] 일일 주식 모니터링 워크플로우 시작...")
        all_analyses: Dict[str, List[Dict[str, Any]]] = {}
        
        for ticker in self.tickers:
            news_items = self.fetch_rss_news(ticker)
            ticker_analyses: List[Dict[str, Any]] = []
            
            for news in news_items:
                analysis = self.analyze_news_with_gemini(ticker, news["title"])
                # 원본 뉴스의 링크와 타이틀 매핑
                analysis["link"] = news["link"]
                analysis["title"] = self.normalize_text(news["title"])
                ticker_analyses.append(analysis)
                
            all_analyses[ticker] = ticker_analyses
            
        report = self.build_report_message(all_analyses)
        self.send_telegram_message(report)
        print("💡 [StockAgent] 워크플로우 완료.")

# 로컬 테스트용
if __name__ == "__main__":
    agent = StockAgent()
    agent.run_daily_workflow()
