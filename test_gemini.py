"""
test_gemini.py
==============
Gemini API 연결 및 요청 형식 단계별 진단 스크립트

실행 방법:
    python test_gemini.py
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows CP949 터미널 인코딩 오류 방지
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import os

# .env 파일 로드
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path, encoding="utf-8")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

BASE_URL = "https://generativelanguage.googleapis.com"
SIMPLE_PROMPT = "Say hello in Korean."


def print_section(title: str) -> None:
    """구분선과 함께 섹션 제목을 출력합니다."""
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print("=" * 55)


def call_gemini(
    model: str,
    api_version: str,
    payload: dict,
    label: str,
) -> None:
    """
    Gemini API를 호출하고 결과 또는 에러를 상세히 출력합니다.

    Args:
        model: 사용할 모델명 (예: gemini-2.0-flash)
        api_version: API 버전 (v1 또는 v1beta)
        payload: 요청 payload 딕셔너리
        label: 테스트 케이스 설명
    """
    url = f"{BASE_URL}/{api_version}/models/{model}:generateContent"
    url += f"?key={GEMINI_API_KEY}"

    print(f"\n[테스트] {label}")
    print(f"  URL     : {BASE_URL}/{api_version}/models/{model}:generateContent")
    print(f"  Payload : {json.dumps(payload, ensure_ascii=False)[:120]}...")

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = (
                body.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "(응답 없음)")
            )
            print(f"  결과   : [OK] 성공")
            print(f"  응답   : {text[:200]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  결과   : [FAIL] HTTP {e.code} {e.reason}")
        try:
            err_json = json.loads(body)
            msg = err_json.get("error", {}).get("message", body[:300])
            print(f"  에러   : {msg}")
        except json.JSONDecodeError:
            print(f"  에러   : {body[:300]}")
    except Exception as e:
        print(f"  결과   : [FAIL] 예외 발생: {e}")


def main() -> None:
    # ── 0. API 키 확인 ────────────────────────────────────
    print_section("0. API 키 확인")
    if not GEMINI_API_KEY or "YOUR_" in GEMINI_API_KEY:
        print("[FAIL] GEMINI_API_KEY가 .env에 설정되지 않았습니다. 테스트를 중단합니다.")
        sys.exit(1)
    masked = GEMINI_API_KEY[:6] + "..." + GEMINI_API_KEY[-4:]
    print(f"  API Key : {masked} (총 {len(GEMINI_API_KEY)}자)")

    # ── 1. 사용 가능한 모델 목록 조회 ────────────────────
    print_section("1. 사용 가능한 모델 목록 (v1beta)")
    models_url = (
        f"{BASE_URL}/v1beta/models?key={GEMINI_API_KEY}"
    )
    try:
        with urllib.request.urlopen(models_url, timeout=10) as resp:
            models = json.loads(resp.read().decode("utf-8"))
            flash_models = [
                m["name"]
                for m in models.get("models", [])
                if "flash" in m["name"].lower()
            ]
            print("  Flash 계열 모델:")
            for m in flash_models[:10]:
                print(f"    - {m}")
    except Exception as e:
        print(f"  ❌ 모델 목록 조회 실패: {e}")

    # ── 2. 기본 텍스트 요청 (v1beta, mimeType 없음) ──────
    call_gemini(
        model="gemini-2.5-flash",
        api_version="v1beta",
        payload={
            "contents": [{"parts": [{"text": SIMPLE_PROMPT}]}]
        },
        label="v1beta / gemini-2.5-flash / mimeType 없음",
    )

    # ── 3. v1 엔드포인트, mimeType 없음 ──────────────────
    call_gemini(
        model="gemini-2.5-flash",
        api_version="v1",
        payload={
            "contents": [{"parts": [{"text": SIMPLE_PROMPT}]}]
        },
        label="v1 / gemini-2.5-flash / mimeType 없음",
    )

    # ── 4. v1beta, responseMimeType: application/json ────
    call_gemini(
        model="gemini-2.5-flash",
        api_version="v1beta",
        payload={
            "contents": [{"parts": [{"text": SIMPLE_PROMPT}]}],
            "generationConfig": {
                "responseMimeType": "application/json"
            },
        },
        label="v1beta / gemini-2.5-flash / mimeType=json",
    )

    # ── 5. v1, responseMimeType: application/json ────────
    call_gemini(
        model="gemini-2.5-flash",
        api_version="v1",
        payload={
            "contents": [{"parts": [{"text": SIMPLE_PROMPT}]}],
            "generationConfig": {
                "responseMimeType": "application/json"
            },
        },
        label="v1 / gemini-2.5-flash / mimeType=json",
    )

    # ── 6. gemini-2.0-flash-lite 폴백 테스트 ─────────────
    call_gemini(
        model="gemini-2.0-flash-lite",
        api_version="v1beta",
        payload={
            "contents": [{"parts": [{"text": SIMPLE_PROMPT}]}]
        },
        label="v1beta / gemini-2.0-flash-lite / mimeType 없음",
    )

    # ── 7. 실제 감성 분석 프롬프트 테스트 ───────────────
    print_section("7. 실제 감성 분석 프롬프트 (성공한 설정으로)")
    actual_prompt = (
        "주식 티커: AAPL\n"
        "뉴스 제목: Apple reports record quarterly earnings\n\n"
        "위의 뉴스가 해당 주가에 미칠 단기적 영향을 분석하고 "
        "반드시 아래 JSON 형식으로만 한국어로 대답해주세요.\n"
        "{\n"
        '  "sentiment": "긍정적/부정적/중립 중 하나",\n'
        '  "impact_score": 0~100 사이 정수,\n'
        '  "summary": "한국어 요약 (3문장 이내)"\n'
        "}"
    )
    call_gemini(
        model="gemini-2.5-flash",
        api_version="v1beta",
        payload={
            "contents": [{"parts": [{"text": actual_prompt}]}]
        },
        label="v1beta / 실제 감성분석 프롬프트 / mimeType 없음",
    )

    print(f"\n{'=' * 55}")
    print("  진단 완료. 위 결과에서 [OK] 성공한 설정을 stock_agent.py에 적용하세요.")
    print("=" * 55)


if __name__ == "__main__":
    main()
