"""
spec_auto_java_parser.py
─────────────────────────────────────────────────────────
SpecAutoAgent - Java Spring Controller 파싱 모듈
업로드된 .java 파일에서 API 스펙을 자동 추출

처리 흐름:
  1. Regex로 어노테이션·구조 1차 추출
  2. GPT-4o에게 전체 코드 분석 요청 → SpecApiSchema 변환

지원 어노테이션:
  매핑   : @RequestMapping, @GetMapping, @PostMapping,
            @PutMapping, @PatchMapping, @DeleteMapping
  파라미터: @RequestBody, @RequestParam, @PathVariable
  검증   : @NotNull, @NotBlank, @Size, @Valid, @Min, @Max
  예외   : @ExceptionHandler, @ResponseStatus
─────────────────────────────────────────────────────────
"""

import re
import json
import os
from dataclasses import dataclass, field
from typing import Optional
from spec_auto_agent.core.spec_auto_client import get_client
from spec_auto_agent.models.spec_auto_models import (
    SpecApiSchema, SpecFieldSchema, SpecErrorSchema, HttpMethod
)

# ─────────────────────────────────────────────
# 1차 파싱 결과 데이터클래스
# ─────────────────────────────────────────────

@dataclass
class JavaEndpoint:
    """Controller 메서드 1개의 파싱 결과"""
    http_method:  str = "POST"
    base_path:    str = ""
    method_path:  str = ""
    method_name:  str = ""
    request_body: str = ""          # @RequestBody 클래스명
    path_vars:    list = field(default_factory=list)   # @PathVariable
    req_params:   list = field(default_factory=list)   # @RequestParam
    return_type:  str = ""
    raw_method:   str = ""          # 메서드 원문

@dataclass
class JavaParseResult:
    """Java 파일 전체 파싱 결과"""
    class_name:   str = ""
    base_path:    str = ""
    endpoints:    list = field(default_factory=list)   # List[JavaEndpoint]
    dto_classes:  dict = field(default_factory=dict)   # 클래스명 → 필드 목록
    error_codes:  list = field(default_factory=list)   # ExceptionHandler 추출
    raw_code:     str = ""

# ─────────────────────────────────────────────
# 정규식 패턴
# ─────────────────────────────────────────────

_RE_CLASS_NAME  = re.compile(r'(?:public\s+class|public\s+\w+\s+class)\s+(\w+)')
_RE_BASE_PATH   = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']')
_RE_METHOD_BLOCK= re.compile(
    r'(@(?:Get|Post|Put|Patch|Delete)Mapping[^)]*\))'
    r'.*?'
    r'(?:public|private|protected)\s+\S+\s+(\w+)\s*\(([^)]*)\)',
    re.DOTALL
)
_RE_MAPPING_PATH= re.compile(r'@(\w+)Mapping\s*\(?\s*(?:value\s*=\s*)?["\']?([^"\')\s]*)["\']?')
_RE_REQ_BODY    = re.compile(r'@RequestBody\s+\w+\s+(\w+)')
_RE_PATH_VAR    = re.compile(r'@PathVariable(?:\([^)]*\))?\s+\w+\s+(\w+)')
_RE_REQ_PARAM   = re.compile(r'@RequestParam(?:\((?:[^)]*?value\s*=\s*)?["\']?(\w+)["\']?[^)]*\))?\s+\w+\s+(\w+)')
_RE_RETURN      = re.compile(r'(?:public|private)\s+([\w<>, ]+?)\s+\w+\s*\(')
_RE_DTO_CLASS   = re.compile(
    r'(?:public\s+)?(?:class|record)\s+(\w+(?:Dto|Request|Response|VO|Req|Res|Param|Body))\b[^{]*\{([^}]+)\}',
    re.IGNORECASE | re.DOTALL
)
_RE_DTO_FIELD   = re.compile(
    r'(?P<annots>(?:@\w+(?:\([^)]*\))?\s*)*)'
    r'(?:private|protected|public)?\s+'
    r'(?P<type>[\w<>, \[\]]+?)\s+'
    r'(?P<name>\w+)\s*;',
    re.DOTALL
)
_RE_EXCEPTION   = re.compile(
    r'@ResponseStatus\s*\([^)]*HttpStatus\.(\w+)[^)]*\).*?'
    r'@ExceptionHandler',
    re.DOTALL
)
_RE_VALIDATION  = re.compile(r'@(NotNull|NotBlank|NotEmpty|Size|Min|Max|Valid|Pattern|Email|Positive)')


# ─────────────────────────────────────────────
# SpecAutoJavaParser
# ─────────────────────────────────────────────

class SpecAutoJavaParser:
    """
    Java Spring Controller 파일 → SpecApiSchema 변환
    SpecAutoAgent 시나리오 A (기존 코드 분석) 담당 컴포넌트
    """

    def __init__(self):
        self.client, self.deployment = get_client()

    # ── Public ──────────────────────────────

    def parse_and_generate(
        self,
        java_code:     str,
        reference_doc: str = "",
    ) -> SpecApiSchema:
        """
        Java 코드 → SpecApiSchema

        Args:
            java_code:     .java 파일 원문
            reference_doc: 기존 규격서 참고 텍스트 (선택)

        Returns:
            SpecApiSchema
        """
        # 1단계: Regex 1차 파싱
        parsed = self._regex_parse(java_code)
        print(f"[SpecAutoJavaParser] 1차 파싱 완료 "
              f"→ class={parsed.class_name}, endpoints={len(parsed.endpoints)}")

        # 2단계: GPT-4o 심층 분석
        schema = self._gpt_analyze(parsed, java_code, reference_doc)
        print(f"[SpecAutoJavaParser] GPT 분석 완료 → {schema.method} {schema.endpoint}")
        return schema

    def regex_parse_only(self, java_code: str) -> JavaParseResult:
        """Regex 1차 파싱 결과만 반환 (GPT 호출 없음)"""
        return self._regex_parse(java_code)

    # ── Private: 1차 Regex 파싱 ─────────────

    def _regex_parse(self, code: str) -> JavaParseResult:
        result = JavaParseResult(raw_code=code)

        # 클래스명
        m = _RE_CLASS_NAME.search(code)
        result.class_name = m.group(1) if m else ""

        # 클래스 레벨 @RequestMapping
        m = _RE_BASE_PATH.search(code)
        result.base_path = m.group(1) if m else ""

        # 메서드 레벨 매핑
        for match in _RE_METHOD_BLOCK.finditer(code):
            annot, mname, params = match.group(1), match.group(2), match.group(3)
            ep = JavaEndpoint(method_name=mname, raw_method=match.group(0))

            # HTTP Method + 경로
            pm = _RE_MAPPING_PATH.search(annot)
            if pm:
                ep.http_method = self._to_http_method(pm.group(1))
                ep.method_path = pm.group(2) or ""
            ep.base_path = result.base_path

            # 파라미터 분석
            ep.request_body = (m2.group(1) if (m2 := _RE_REQ_BODY.search(params)) else "")
            ep.path_vars    = _RE_PATH_VAR.findall(params)
            ep.req_params   = [g[1] or g[0] for g in _RE_REQ_PARAM.findall(params)]

            # 반환 타입
            m2 = _RE_RETURN.search(match.group(0))
            ep.return_type = m2.group(1).strip() if m2 else ""

            result.endpoints.append(ep)

        # DTO 클래스 파싱
        for dto_match in _RE_DTO_CLASS.finditer(code):
            cls_name = dto_match.group(1)
            body     = dto_match.group(2)
            fields   = []
            for fm in _RE_DTO_FIELD.finditer(body):
                annots   = fm.group('annots') or ""
                required = bool(_RE_VALIDATION.search(annots))
                fields.append({
                    "name":     fm.group('name'),
                    "type":     fm.group('type').strip(),
                    "required": required,
                    "annotations": re.findall(r'@\w+', annots),
                })
            result.dto_classes[cls_name] = fields

        # ExceptionHandler 에러 코드 추출
        http_status_map = {
            "BAD_REQUEST": "400", "UNAUTHORIZED": "401",
            "FORBIDDEN": "403",   "NOT_FOUND": "404",
            "CONFLICT": "409",    "INTERNAL_SERVER_ERROR": "500",
        }
        for em in _RE_EXCEPTION.finditer(code):
            status = em.group(1)
            if status in http_status_map:
                result.error_codes.append(http_status_map[status])

        return result

    # ── Private: GPT-4o 심층 분석 ───────────

    def _gpt_analyze(
        self,
        parsed:       JavaParseResult,
        java_code:    str,
        reference_doc:str,
    ) -> SpecApiSchema:

        # 1차 파싱 요약 조립
        ep_summary = ""
        for ep in parsed.endpoints:
            full_path = (ep.base_path + ep.method_path).replace("//", "/") or "/v1/unknown"
            ep_summary += (
                f"- {ep.http_method} {full_path} "
                f"(메서드: {ep.method_name}, "
                f"RequestBody: {ep.request_body}, "
                f"PathVars: {ep.path_vars}, "
                f"ReqParams: {ep.req_params})\n"
            )

        dto_summary = ""
        for cls, fields in parsed.dto_classes.items():
            dto_summary += f"\n[{cls}]\n"
            for f in fields:
                dto_summary += (
                    f"  - {f['name']}: {f['type']} "
                    f"{'(필수)' if f['required'] else '(선택)'} "
                    f"{f['annotations']}\n"
                )

        ref_section = (
            f"\n[기존 규격서 참고 - 아래 패턴/용어를 최대한 유지하세요]\n{reference_doc[:3000]}"
            if reference_doc.strip() else ""
        )

        prompt = f"""다음 Java Spring Controller 코드를 분석하여 API 규격서 JSON Schema를 생성하세요.

[1차 파싱 결과]
클래스: {parsed.class_name}
엔드포인트:
{ep_summary}
DTO 클래스:
{dto_summary}
에러 코드 감지: {parsed.error_codes}
{ref_section}

[전체 소스코드]
{java_code[:4000]}

위 정보를 바탕으로 가장 첫 번째 또는 핵심 엔드포인트에 대해
정확한 JSON Schema를 반환하세요.
코드와 100% 일치해야 합니다. 추측하지 말고 코드에 있는 내용만 사용하세요.
"""
        system_prompt = """You are SpecAutoJavaParser inside SpecAutoAgent.
Analyze Java Spring Controller code and output ONLY a JSON object following this schema:
{
  "api_name": "short English name",
  "endpoint": "/v1/...",
  "method": "GET|POST|PUT|PATCH|DELETE",
  "description": "Korean description",
  "version": "v1",
  "request": [{"name":"","type":"","required":true,"description":"","example":null,"format":null,"enum":null}],
  "response": [{"name":"","type":"","required":true,"description":"","example":null,"format":null,"enum":null}],
  "errors": [{"code":"400","description":"한국어 설명"}],
  "headers": {"Content-Type":"application/json"},
  "auth_required": true,
  "tags": []
}
Output ONLY valid JSON. Extract ONLY from the actual code — do not invent fields."""

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        raw  = response.choices[0].message.content
        data = json.loads(raw)

        return SpecApiSchema(
            api_name      = data.get("api_name", parsed.class_name),
            endpoint      = data.get("endpoint", "/v1/unknown"),
            method        = HttpMethod(data.get("method", "POST")),
            description   = data.get("description", ""),
            version       = data.get("version", "v1"),
            request       = [SpecFieldSchema(**f) for f in data.get("request", [])],
            response      = [SpecFieldSchema(**f) for f in data.get("response", [])],
            errors        = [SpecErrorSchema(**e) for e in data.get("errors", [])],
            headers       = data.get("headers", {}),
            auth_required = data.get("auth_required", True),
            tags          = data.get("tags", []),
        )

    @staticmethod
    def _to_http_method(annotation_prefix: str) -> str:
        mapping = {
            "Get": "GET", "Post": "POST", "Put": "PUT",
            "Patch": "PATCH", "Delete": "DELETE",
        }
        return mapping.get(annotation_prefix, "POST")
