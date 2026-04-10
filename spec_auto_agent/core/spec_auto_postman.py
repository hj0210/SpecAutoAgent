"""
spec_auto_postman.py
─────────────────────────────────────────────────────────
SpecAutoAgent - Step 2: Postman Collection 자동 생성
SpecApiSchema → Postman Collection v2.1 JSON
─────────────────────────────────────────────────────────
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from spec_auto_agent.models.spec_auto_models import SpecApiSchema, HttpMethod

OUTPUT_DIR = Path(__file__).parent.parent / "output"


class SpecAutoPostman:
    """
    SpecApiSchema → Postman Collection v2.1 JSON 자동 생성
    Import 즉시 테스트 가능한 형태로 출력
    SpecAutoAgent Step 2 테스트 에셋 담당 컴포넌트
    """

    def __init__(self, base_url: str = "{{base_url}}"):
        self.base_url = base_url
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def build(self, schema: SpecApiSchema) -> tuple[dict, str]:
        """
        Postman Collection JSON 생성 및 파일 저장

        Returns:
            (collection_dict, file_path)
        """
        print(f"[SpecAutoPostman] Postman Collection 생성 시작...")

        req_body  = {f.name: f.example if f.example is not None else self._default(f.type)
                     for f in schema.request}
        res_body  = {f.name: f.example if f.example is not None else self._default(f.type)
                     for f in schema.response}

        collection = {
            "info": {
                "_postman_id": str(uuid.uuid4()),
                "name":        f"[SpecAutoAgent] {schema.api_name}",
                "schema":      "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "description": f"SpecAutoAgent 자동 생성 | {schema.description} | {self._ts()}"
            },
            "variable": [
                {"key": "base_url", "value": "http://localhost:8000", "type": "string"}
            ],
            "item": [
                {
                    "name": f"{schema.method} {schema.api_name}",
                    "event": [{
                        "listen": "test",
                        "script": {
                            "exec": [
                                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                                f"pm.test('Has required field', () => pm.expect(pm.response.json()).to.have.property('{schema.response[0].name if schema.response else 'data'}'));",
                            ],
                            "type": "text/javascript"
                        }
                    }],
                    "request": {
                        "method": schema.method.value,
                        "header": [
                            {"key": "Content-Type", "value": "application/json"},
                            {"key": "Authorization", "value": "Bearer {{access_token}}",
                             "disabled": not schema.auth_required},
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps(req_body, ensure_ascii=False, indent=2),
                            "options": {"raw": {"language": "json"}}
                        } if schema.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH] else None,
                        "url": {
                            "raw":  f"{self.base_url}{schema.endpoint}",
                            "host": [self.base_url],
                            "path": schema.endpoint.strip("/").split("/"),
                        }
                    },
                    "response": [{
                        "name":   "Success 200",
                        "status": "OK",
                        "code":   200,
                        "_postman_previewlanguage": "json",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body":   json.dumps(res_body, ensure_ascii=False, indent=2)
                    }]
                },
                *self._error_items(schema)
            ]
        }

        path = str(OUTPUT_DIR / f"spec_auto_postman_{schema.api_name.replace(' ', '_')}_{self._ts()}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(collection, f, ensure_ascii=False, indent=2)

        print(f"[SpecAutoPostman] Postman Collection 생성 완료: {path}")
        return collection, path

    def _error_items(self, schema):
        return [{
            "name": f"Error {e.code} - {e.description}",
            "request": {
                "method": schema.method.value,
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {"mode": "raw",
                         "raw": json.dumps({"_test_case": f"error_{e.code}"}, ensure_ascii=False),
                         "options": {"raw": {"language": "json"}}},
                "url": {"raw":  f"{self.base_url}{schema.endpoint}",
                        "host": [self.base_url],
                        "path": schema.endpoint.strip("/").split("/")}
            }
        } for e in schema.errors]

    def _default(self, t):
        return {"string": "example", "integer": 1, "boolean": True,
                "object": {}, "array": [], "number": 0.0}.get(t, "example")

    def _ts(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")
