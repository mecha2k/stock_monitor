# Stock Monitor - 프로젝트 문서

> 미국 주식 뉴스를 자동 수집·AI 분석하여 텔레그램으로 일일 리포트를 발송하는 Python 에이전트 시스템

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **목적** | 지정된 미국 주식 티커의 최신 뉴스를 RSS로 수집하고 Gemini LLM으로 감성 분석 후 텔레그램 알림 발송 |
| **실행 환경** | standard Python 가상환경 (`.venv`, uv 관리) |
| **Python 버전** | Python 3.x (PEP 8 / Type Hinting 준수) |
| **알림 시각** | 매일 오전 08:00 KST (설정 변경 가능) |
| **핵심 라이브러리** | `python-telegram-bot v22.7`, `feedparser`, `python-dotenv` |

---

## 2. 프로젝트 구조

```
stock_monitor/
├── .env                  # 🔐 API 키 / 토큰 저장 (Git 제외)
├── .gitignore            # Git 추적 제외 규칙
├── config.py             # 전역 설정 관리 (.env 자동 로드)
├── stock_agent.py        # 핵심 에이전트 (뉴스 수집 → 분석 → 리포트)
├── telegram_bot.py       # Telegram Bot API 전용 모듈
├── scheduler.py          # KST 기반 일일 스케줄러
├── requirements.txt      # Python 의존성 목록
└── project.md            # 프로젝트 문서 (현재 파일)
```

---

## 3. 아키텍처 흐름도

```
┌─────────────────────────────────────────────────────┐
│                   scheduler.py                      │
│   매일 08:00 KST에 StockAgent.run_daily_workflow()  │
│   트리거 (30초 주기 폴링, 중복 실행 방지)             │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                  stock_agent.py                     │
│                                                     │
│  1. fetch_rss_news(ticker)                          │
│     └─ Yahoo Finance RSS → 최신 뉴스 최대 3건       │
│                                                     │
│  2. analyze_news_with_gemini(ticker, title)         │
│     └─ Gemini API → 감성(긍정/부정/중립),           │
│        영향도 점수(0~100), 한국어 요약               │
│     └─ API 키 없음 / 오류 시 → _mock_analysis()    │
│                                                     │
│  3. build_report_message(all_analyses)              │
│     └─ HTML 포맷 텔레그램 메시지 조립               │
│                                                     │
│  4. send_telegram_message(message)                  │
│     └─ urllib 기반 직접 API 호출 (레거시 방식)       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│               telegram_bot.py  (신규)               │
│                                                     │
│  TelegramNotifier 클래스                            │
│  ├─ send_message()         비동기 메시지 전송        │
│  ├─ send_message_sync()    동기 래퍼 (기존 코드 호환)│
│  ├─ send_photo()           이미지 전송               │
│  └─ verify_connection()    봇 연결 상태 검증         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              📱 Telegram 채팅 수신
```

---

## 4. 파일별 상세 설명

### 4.1 `.env` — 민감 정보 저장소

```env
TELEGRAM_BOT_TOKEN=실제_봇_토큰_입력
TELEGRAM_CHAT_ID=실제_채팅_ID_입력
GEMINI_API_KEY=실제_Gemini_API_키_입력
```

> ⚠️ **절대 Git에 커밋하지 마세요.** `.gitignore`에 이미 등록되어 있습니다.

- **TELEGRAM_BOT_TOKEN**: [@BotFather](https://t.me/BotFather) 에서 봇 생성 후 발급
- **TELEGRAM_CHAT_ID**: [@userinfobot](https://t.me/userinfobot) 에 메시지 전송 시 확인 가능
- **GEMINI_API_KEY**: [Google AI Studio](https://aistudio.google.com/) 에서 발급

---

### 4.2 `config.py` — 전역 설정 관리

`python-dotenv`를 통해 `.env` 파일을 자동 로드합니다.

| 상수 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `TARGET_STOCKS` | `List[str]` | `["AAPL", "GOOGL", "TSLA"]` | 모니터링 대상 티커 |
| `TELEGRAM_BOT_TOKEN` | `str` | `.env` 로드 | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | `str` | `.env` 로드 | 텔레그램 채팅 ID |
| `GEMINI_API_KEY` | `str` | `.env` 로드 | Gemini API 키 |
| `NOTIFICATION_TIME` | `str` | `"08:00"` | 알림 발송 시각 (KST) |

**우선순위**: 시스템 환경 변수 > `.env` 파일 > 코드 내 기본값

---

### 4.3 `stock_agent.py` — 핵심 에이전트

`StockAgent` 클래스의 주요 메서드:

| 메서드 | 역할 |
|---|---|
| `fetch_rss_news(ticker)` | Yahoo Finance RSS 피드에서 최신 뉴스 3건 수집 |
| `analyze_news_with_gemini(ticker, title)` | Gemini API로 감성 분석 (실패 시 Mock 대체) |
| `_mock_analysis(ticker, title)` | API 오류 시 키워드 기반 로컬 폴백 분석 |
| `send_telegram_message(message)` | urllib 기반 텔레그램 메시지 직접 전송 (레거시) |
| `build_report_message(all_analyses)` | HTML 포맷 리포트 메시지 조립 |
| `run_daily_workflow()` | 전체 워크플로우 실행 (수집 → 분석 → 전송) |
| `normalize_text(text)` | NFC 정규화로 한글 자소 깨짐 방지 |

**Gemini 응답 JSON 스키마:**
```json
{
  "sentiment": "긍정적 | 부정적 | 중립",
  "impact_score": 0~100,
  "summary": "한국어 요약 (3문장 이내)"
}
```

---

### 4.4 `telegram_bot.py` — Telegram Bot API 전용 모듈 (신규)

`python-telegram-bot v22.7` 기반의 고수준 추상화 클래스입니다.

```python
from telegram_bot import TelegramNotifier

# .env에서 자동으로 토큰/채팅ID 로드
notifier = TelegramNotifier()

# 비동기 방식 (async 환경)
await notifier.send_message("<b>📈 분석 완료!</b>")

# 동기 방식 (기존 동기 코드에서 호출)
notifier.send_message_sync("분석 완료!")
```

| 메서드 | 방식 | 설명 |
|---|---|---|
| `send_message(text)` | async | HTML 포맷 메시지 전송 |
| `send_message_sync(text)` | sync | 동기 래퍼 (별도 스레드 이벤트 루프) |
| `send_photo(path, caption)` | async | 로컬 이미지 파일 전송 |
| `verify_connection()` | async | 봇 토큰 유효성 및 연결 상태 검증 |

**v22 주요 변경사항 반영:**
- `disable_web_page_preview` → `LinkPreviewOptions(is_disabled=True)` 대체

---

### 4.5 `scheduler.py` — 일일 스케줄러

KST 기준 매일 지정 시각에 에이전트를 자동 실행합니다.

```python
# 실행 방법
python scheduler.py
```

- 30초 단위로 현재 시각을 폴링하여 `NOTIFICATION_TIME`과 비교
- `last_run_date`로 하루 1회만 실행 보장 (중복 방지)
- `KeyboardInterrupt` 시 정상 종료, 예외 발생 시 60초 후 자동 재시도

---

## 5. 설치 및 실행 가이드

### 5.1 환경 설정

```bash
# 가상환경 생성 및 의존성 설치 (uv를 사용하여 메모리 및 디스크 용량 최소화)
uv venv .venv
uv pip install -r requirements.txt
```

### 5.2 `.env` 파일 설정

`.env` 파일을 열고 실제 값을 입력합니다:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef_실제_토큰
TELEGRAM_CHAT_ID=123456789
GEMINI_API_KEY=AIzaSy_실제_키
```

### 5.3 봇 연결 테스트

```bash
# uv run을 사용하여 가상환경 활성화 없이 즉시 실행:
uv run python telegram_bot.py
# 또는 직접 가상환경 내의 인터프리터 사용:
# Linux/macOS: ./.venv/bin/python telegram_bot.py
# Windows: .\.venv\Scripts\python.exe telegram_bot.py
```

텔레그램에서 테스트 메시지가 수신되면 정상입니다.

### 5.4 즉시 1회 실행 (테스트)

```bash
uv run python stock_agent.py
```

### 5.5 스케줄러 상시 실행

```bash
uv run python scheduler.py
```

---

## 6. 의존성 목록 (`requirements.txt`)

| 패키지 | 버전 | 용도 |
|---|---|---|
| `feedparser` | ≥ 6.0.10 | Yahoo Finance RSS 피드 파싱 |
| `python-dotenv` | ≥ 1.0.0 | `.env` 파일 자동 로드 |
| `python-telegram-bot` | ≥ 21.0 (설치: 22.7) | Telegram Bot API 클라이언트 |

---

## 7. 보안 가이드라인

| 항목 | 상태 | 설명 |
|---|---|---|
| `.env` Git 제외 | ✅ 완료 | `.gitignore`에 등록됨 |
| 토큰 하드코딩 금지 | ✅ 완료 | 환경 변수 / `.env` 방식으로만 관리 |
| 플레이스홀더 감지 | ✅ 완료 | 기본값 감지 시 즉시 예외 처리 |
| `.env.example` 제공 | ⬜ 미완 | 팀 협업 시 생성 권장 |

---

## 8. 향후 개선 검토 사항

- [ ] `stock_agent.py`의 레거시 `urllib` 방식을 `TelegramNotifier`로 교체
- [ ] `scheduler.py`를 `APScheduler` 또는 `schedule` 라이브러리로 고도화
- [ ] 주가 실시간 데이터 연동 (yfinance 등)
- [ ] 뉴스 중복 필터링 (이미 발송된 뉴스 재발송 방지)
- [ ] Docker 컨테이너화 또는 Cloud Run 배포
- [ ] `.env.example` 파일 생성 (팀 협업용 가이드)
