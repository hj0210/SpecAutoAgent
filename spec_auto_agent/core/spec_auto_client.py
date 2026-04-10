"""
spec_auto_client.py
─────────────────────────────────────────────────────────
SpecAutoAgent - AI 클라이언트 팩토리
.env 값에 따라 3가지 모드 자동 선택

우선순위: Azure OpenAI > Google Gemini > OpenAI

로컬 무료  → USE_GEMINI=true  + GEMINI_API_KEY
로컬 유료  → USE_AZURE=false  + OPENAI_API_KEY
Azure 배포 → USE_AZURE=true   + AZURE_OPENAI_* 설정
─────────────────────────────────────────────────────────
"""

import os
from openai import OpenAI, AzureOpenAI

# Gemini OpenAI-호환 엔드포인트 (신규 패키지 설치 불필요)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_client() -> tuple[OpenAI | AzureOpenAI, str]:
    """
    환경변수 값에 따라 클라이언트와 모델명 반환

    Returns:
        (client, model_or_deployment_name)
    """
    use_azure  = os.getenv("USE_AZURE",  "false").lower() == "true"
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

    if use_azure:
        # ── Azure OpenAI ──────────────────────────────
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        print(f"[SpecAutoClient] Azure OpenAI 사용 → deployment: {model}")

    elif use_gemini:
        # ── Google Gemini (OpenAI 호환, 무료 티어) ────
        client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=GEMINI_BASE_URL,
        )
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        print(f"[SpecAutoClient] Google Gemini 사용 → model: {model}")

    else:
        # ── OpenAI (유료) ────────────────────────────
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"[SpecAutoClient] OpenAI 사용 → model: {model}")

    return client, model
