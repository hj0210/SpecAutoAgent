"""
spec_auto_analyzer.py
─────────────────────────────────────────────────────────
SpecAutoAgent - Step 1: 의도 분석 & JSON Schema 생성
OpenAI 또는 Azure OpenAI 를 호출하여 자연어 → API 스펙 변환
USE_AZURE=false → OpenAI (로컬 개발)
USE_AZURE=true  → Azure OpenAI (운영/배포)
─────────────────────────────────────────────────────────
"""

import json
import os
from openai import RateLimitError, AuthenticationError, APIConnectionError, NotFoundError
from spec_auto_agent.core.spec_auto_client import get_client
from spec_auto_agent.core.spec_auto_java_parser import SpecAutoJavaParser
from spec_auto_agent.models.spec_auto_models import (
    SpecApiSchema, SpecFieldSchema, SpecErrorSchema, HttpMethod
)

# ─────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────

SPEC_AUTO_SYSTEM_PROMPT = """
You are SpecAutoAnalyzer, an expert API specification designer working inside SpecAutoAgent.

When a user describes an API in natural language, analyze it and output a JSON object
that strictly follows the schema below. No explanation, no markdown — only pure JSON.

Output JSON Schema:
{
  "api_name": "string (short English name for the API)",
  "endpoint": "string (e.g. /v1/user/signup)",
  "method": "POST | GET | PUT | PATCH | DELETE",
  "description": "string (one-line description in Korean)",
  "version": "v1",
  "request": [
    {
      "name": "field_name",
      "type": "string | integer | boolean | object | array",
      "required": true,
      "description": "설명 (Korean)",
      "example": "example_value",
      "format": null,
      "enum": null
    }
  ],
  "response": [
    {
      "name": "field_name",
      "type": "string",
      "required": true,
      "description": "설명 (Korean)",
      "example": "example_value",
      "format": null,
      "enum": null
    }
  ],
  "errors": [
    { "code": "400", "description": "오류 설명 (Korean)" }
  ],
  "headers": { "Content-Type": "application/json" },
  "auth_required": true,
  "tags": ["tag1"]
}

Rules:
- Infer all fields intelligently from the user's context
- Use Korean for all description fields
- Endpoint must start with /v1/
- Always include common error codes (400, 401, 409, 500)
- Output ONLY valid JSON. No extra text.
"""


# ─────────────────────────────────────────────
# SpecAutoAnalyzer 클래스
# ─────────────────────────────────────────────

class SpecAutoAnalyzer:
    """
    사용자의 자연어 입력을 받아 GPT-4o로 API 스펙(JSON Schema)을 생성합니다.
    SpecAutoAgent Step 1 담당 컴포넌트
    """

    def __init__(self):
        self.client, self.deployment = get_client()

    def analyze(self, user_input: str) -> SpecApiSchema:
        """자연어 단일 텍스트 → SpecApiSchema"""
        print(f"[SpecAutoAnalyzer] 분석 시작: '{user_input[:50]}...'")
        return self._call_gpt(user_input)

    def analyze_structured(
        self,
        purpose:   str,
        features:  str,
        fields:    str,
        notes:     str = "",
        reference: str = "",
    ) -> SpecApiSchema:
        """
        구조화된 입력 (목적/기능/필드/특이사항) → SpecApiSchema
        기존 규격서 참고 텍스트(reference)가 있으면 컨텍스트로 추가
        """
        # 구조화 입력을 하나의 명확한 프롬프트로 조합
        prompt_parts = [
            f"[API 목적]\n{purpose}",
            f"[주요 기능]\n{features}",
            f"[필요 파라미터/필드]\n{fields}",
        ]
        if notes.strip():
            prompt_parts.append(f"[특이사항]\n{notes}")
        if reference.strip():
            prompt_parts.append(
                f"[기존 규격서 참고 내용 — 아래 패턴/스타일을 참고하여 스펙을 설계하세요]\n{reference[:3000]}"
            )

        prompt = "\n\n".join(prompt_parts)
        print(f"[SpecAutoAnalyzer] 구조화 분석 시작: 목적={purpose[:30]}")
        return self._call_gpt(prompt)

    def analyze_from_java(self, java_code: str, reference_doc: str = "") -> SpecApiSchema:
        """
        Scenario A: Java Spring Controller 소스코드 → SpecApiSchema
        Regex 1차 파싱 + GPT-4o 심층 분석 하이브리드
        """
        print(f"[SpecAutoAnalyzer] Java 코드 분석 시작 ({len(java_code)} bytes)")
        parser = SpecAutoJavaParser()
        return parser.parse_and_generate(java_code, reference_doc)

    def _call_gpt(self, user_prompt: str) -> SpecApiSchema:
        # Gemini는 response_format 미지원 → 프롬프트로 JSON 강제
        is_gemini = self.deployment.lower().startswith("gemini")

        create_kwargs = dict(
            model=self.deployment,
            messages=[
                {"role": "system", "content": SPEC_AUTO_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        if not is_gemini:
            create_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**create_kwargs)

        except RateLimitError as e:
            provider = "Gemini" if is_gemini else "OpenAI"
            key_env  = "GEMINI_API_KEY" if is_gemini else "OPENAI_API_KEY"
            raise RuntimeError(
                f"[{provider}] API 사용 한도를 초과했습니다. "
                f".env 파일의 {key_env} 를 확인하거나 새 키를 발급받으세요."
            ) from e

        except AuthenticationError as e:
            provider = "Gemini" if is_gemini else "OpenAI"
            key_env  = "GEMINI_API_KEY" if is_gemini else "OPENAI_API_KEY"
            raise RuntimeError(
                f"[{provider}] API 키 인증에 실패했습니다. "
                f".env 파일의 {key_env} 값을 확인해 주세요."
            ) from e

        except NotFoundError as e:
            raise RuntimeError(
                f"[모델 오류] '{self.deployment}' 모델을 찾을 수 없습니다. "
                f".env 파일의 모델명을 확인해 주세요. "
                f"(Gemini: gemini-1.5-flash / OpenAI: gpt-4o, gpt-4o-mini)"
            ) from e

        except APIConnectionError as e:
            provider = "Gemini" if is_gemini else "OpenAI"
            raise RuntimeError(
                f"[{provider}] 서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
            ) from e

        except Exception as e:
            raise RuntimeError(f"[AI 호출 오류] {str(e)}") from e

        raw_json = response.choices[0].message.content
        print(f"[SpecAutoAnalyzer] 응답 수신 완료 (model: {self.deployment})")

        # Gemini는 가끔 ```json ``` 코드블록으로 감싸서 반환 → 제거
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
            raw_json = raw_json.strip()

        return self._parse(raw_json)

    def _parse(self, raw_json: str) -> SpecApiSchema:
        data = json.loads(raw_json)
        return SpecApiSchema(
            api_name=data.get("api_name", "Unknown API"),
            endpoint=data.get("endpoint", "/v1/unknown"),
            method=HttpMethod(data.get("method", "POST")),
            description=data.get("description", ""),
            version=data.get("version", "v1"),
            request=[SpecFieldSchema(**f) for f in data.get("request", [])],
            response=[SpecFieldSchema(**f) for f in data.get("response", [])],
            errors=[SpecErrorSchema(**e) for e in data.get("errors", [])],
            headers=data.get("headers", {}),
            auth_required=data.get("auth_required", True),
            tags=data.get("tags", []),
        )
