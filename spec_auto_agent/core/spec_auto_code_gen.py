"""
spec_auto_code_gen.py
─────────────────────────────────────────────────────────
SpecAutoAgent - Step 2: 샘플 코드 자동 생성
SpecApiSchema → Python(FastAPI) / Java(Spring Boot) 코드 생성
─────────────────────────────────────────────────────────
"""

import os
from pathlib import Path
from datetime import datetime
from spec_auto_agent.core.spec_auto_client import get_client
from spec_auto_agent.models.spec_auto_models import SpecApiSchema, CodeLanguage

OUTPUT_DIR = Path(__file__).parent.parent / "output"

PYTHON_SYSTEM_PROMPT = """
You are SpecAutoCodeGen, an expert Python/FastAPI developer inside SpecAutoAgent.
Based on the API spec JSON, generate production-ready Python code including:
1. Pydantic Request/Response models
2. FastAPI router with the endpoint
3. Service layer with basic logic and Korean comments
Output only Python code. No explanation, no markdown fences.
"""

JAVA_SYSTEM_PROMPT = """
You are SpecAutoCodeGen, an expert Java/Spring Boot developer inside SpecAutoAgent.
Based on the API spec JSON, generate production-ready Java code including:
1. Request/Response DTO classes (with Lombok)
2. Controller class with the endpoint
3. Service interface + implementation with basic logic and Korean comments
Output only Java code. No explanation, no markdown fences.
"""


class SpecAutoCodeGen:
    """
    SpecApiSchema → Python(FastAPI) / Java(Spring Boot) 샘플 코드 자동 생성
    SpecAutoAgent Step 2 코드 생성 담당 컴포넌트
    """

    def __init__(self):
        self.client, self.deployment = get_client()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, schema: SpecApiSchema, language: CodeLanguage = CodeLanguage.PYTHON) -> tuple[str, str]:
        """
        샘플 코드 생성 후 파일 저장

        Returns:
            (code_str, file_path)
        """
        print(f"[SpecAutoCodeGen] {language.value} 코드 생성 시작...")

        system_prompt = PYTHON_SYSTEM_PROMPT if language == CodeLanguage.PYTHON else JAVA_SYSTEM_PROMPT

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"다음 API 스펙을 기반으로 코드를 생성해줘:\n\n{schema.model_dump_json(indent=2)}"},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        code = self._strip_fence(response.choices[0].message.content)
        ext  = "py" if language == CodeLanguage.PYTHON else "java"
        path = str(OUTPUT_DIR / f"spec_auto_code_{schema.api_name.replace(' ', '_')}_{self._ts()}.{ext}")

        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        print(f"[SpecAutoCodeGen] 코드 생성 완료: {path}")
        return code, path

    def _strip_fence(self, text: str) -> str:
        lines = text.strip().splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)

    def _ts(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")
