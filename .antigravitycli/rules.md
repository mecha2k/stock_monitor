# Stock Monitor 프로젝트 전용 규칙
# Antigravity IDE 프로젝트 규칙 파일 (우선순위: 전역 규칙보다 높음)

## 1. Python 환경

- **Python 환경**: 메모리/용량 절약을 위해 conda를 사용하지 않고
  standard Python 가상환경(`.venv`)과 `uv` 패키지 매니저를 사용합니다.
  - Python 인터프리터 경로:
    - Linux/macOS: `./.venv/bin/python`
    - Windows: `.\.venv\Scripts\python.exe`
- **패키지 설치**: `uv pip install <패키지>` 사용
- **실행 방식**: `uv run python <스크립트>` 또는 가상환경 내의 Python 인터프리터로 직접 실행

## 2. 코드 스타일

- **포매터**: Black (`--line-length 80`)
- **라인 최대 길이**: **80자** (모든 소스 및 문서 파일의 라인은 80자 이내로 제한)
- **저장 시 자동 포매팅**: `.vscode/settings.json`의 `formatOnSave: true` 적용 중
- **긴 문자열 처리**: 괄호 안 묵시적 문자열 연결(implicit string concatenation) 사용
  ```python
  # 올바른 예시
  message = (
      f"앞부분 {variable} 이어지는 "
      "뒷부분 텍스트입니다."
  )
  ```
- **f-string**: 모든 문자열 포매팅에 f-string 사용
- **파일 입출력 인코딩**: 모든 `open()` 호출에 `encoding="utf-8"` 명시

## 3. 프로젝트 구조

```
stock_monitor/
├── config.py          # 환경변수 로드 및 설정값 관리
├── stock_agent.py     # 핵심 에이전트 (뉴스 수집 + Gemini 분석 + 텔레그램 전송)
├── telegram_bot.py    # 텔레그램 봇 클라이언트 (python-telegram-bot v21+)
├── scheduler.py       # APScheduler 기반 일일 스케줄링
├── get_chat_id.py     # 텔레그램 Chat ID 조회 유틸리티
├── requirements.txt   # 의존성 패키지 목록
└── .env               # 비밀 키 및 환경변수 (절대 커밋 금지)
```

## 4. 외부 API 규칙

### Gemini API
- **엔드포인트**: `{GEMINI_BASE_URL}/{model}:generateContent`
- **현재 모델**: `gemini-2.5-flash` (최신 가용 모델)
- **API 버전**: `v1beta` 사용
  - `v1`은 `responseMimeType` 필드 미지원 (400 오류 발생)
- **`responseMimeType`**: payload에 포함 금지 (v1beta 전용 필드로 v1에서 400 Bad Request 발생)
- **timeout**: `30`심 (gemini-2.5-flash 추론 시간 고려, 10초 부족)
- **응답 파싱**: 응답이 \`\`\`json ... \`\`\` 마크다운 블록으로 감싸지는 경우가 있으므로 자동 제거 로직 필수
  ```python
  if response_text.startswith("```"):
      lines = response_text.splitlines()
      response_text = "\n".join(lines[1:-1]).strip()
  ```
- **키 미설정 시**: Mock 분석 엔진으로 자동 폴백
- **Windows 터미널**: `sys.stdout.reconfigure(encoding="utf-8")` 필수 (이모지 출력 오류 방지)

### Telegram Bot API
- **라이브러리**: `python-telegram-bot >= 21.0` (v22+ 호환)
- **파싱 모드**: `ParseMode.HTML` 사용
- **URL 미리보기**: `LinkPreviewOptions(is_disabled=True)` 사용
  (deprecated된 `disable_web_page_preview` 사용 금지)

## 5. 환경변수 (.env)

```ini
TELEGRAM_BOT_TOKEN=실제_봇_토큰
TELEGRAM_CHAT_ID=실제_채팅_ID
GEMINI_API_KEY=실제_Gemini_API_키
```

- `.env` 파일은 `.gitignore`에 등록되어 있어야 합니다.
- `load_dotenv(encoding="utf-8")` 명시 필수

## 6. 한국어 처리 및 답변 언어

- **답변 언어 규정**: AI 어시스턴트(Antigravity)는 사용자의 모든 질문과 요청에 대한 답변을 항상 한국어(Korean)로 작성해야 합니다. 영어나 타 언어로 요청이 들어오더라도 시스템 보고 및 로그 확인을 제외한 사용자 대상 답변은 반드시 한국어로 수행합니다.
- 모든 사용자 노출 문자열은 한국어로 작성
- 유니코드 정규화: `unicodedata.normalize("NFC", text)` 적용
- 한국 표준시(KST, UTC+9) 기준으로 시간 처리:
  ```python
  KST = timezone(timedelta(hours=9))
  datetime.now(KST)
  ```

## 7. 에러 처리

- 모든 외부 API 호출은 `try/except`로 감싸고, 실패 시 폴백 처리
- 로그는 `logging` 모듈 사용 (`print` 대신 `logger.info/error` 권장)

## 8. 인코딩 규칙

- **파일 입출력**: `open(path, encoding="utf-8")` 명시
- **dotenv 로드**: `load_dotenv(dotenv_path=..., encoding="utf-8")` 명시
- **Windows 환경변수**: `PYTHONUTF8=1` 설정으로 CP949 충돌 방지
- **subprocess/터미널 출력**: 필요 시 `sys.stdout.reconfigure(encoding="utf-8")` 적용

```python
# 올바른 파일 읽기 예시
with open("data.txt", encoding="utf-8") as f:
    content = f.read()

# 올바른 파일 쓰기 예시
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(content)
```
