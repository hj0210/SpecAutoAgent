"""
spec_auto_models.py
─────────────────────────────────────────────────────────
SpecAutoAgent - Pydantic 데이터 모델 정의
Request / Response / 내부 Schema 모델 통합 관리
─────────────────────────────────────────────────────────
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ─────────────────────────────────────────────
# Enum 정의
# ─────────────────────────────────────────────

class HttpMethod(str, Enum):
    GET    = "GET"
    POST   = "POST"
    PUT    = "PUT"
    PATCH  = "PATCH"
    DELETE = "DELETE"


class OutputFormat(str, Enum):
    EXCEL   = "excel"
    WORD    = "word"
    POSTMAN = "postman"
    CODE    = "code"
    ALL     = "all"


class CodeLanguage(str, Enum):
    PYTHON = "python"
    JAVA   = "java"


# ─────────────────────────────────────────────
# Step 0: 사용자 입력 모델
# ─────────────────────────────────────────────

class SpecAutoRequest(BaseModel):
    """사용자 자연어 입력 요청 모델 (단일 텍스트)"""
    user_input: str = Field(
        ...,
        description="자연어로 작성된 API 요구사항",
        example="회원가입 API 만들어줘. 아이디, 비번, 이메일이 필요하고 중복 체크 기능도 있어야 해."
    )
    output_formats: List[OutputFormat] = Field(
        default=[OutputFormat.ALL],
        description="생성할 산출물 종류"
    )
    code_language: CodeLanguage = Field(
        default=CodeLanguage.PYTHON,
        description="샘플 코드 생성 언어"
    )
    author: Optional[str] = Field(
        default="SpecAutoAgent",
        description="문서 작성자명"
    )


class SpecAutoStructuredRequest(BaseModel):
    """구조화된 입력 요청 모델 (UI 전용)"""
    purpose:    str = Field(..., description="API 목적 (한 줄 요약)", example="회원가입 처리")
    features:   str = Field(..., description="주요 기능 설명", example="중복 체크, 이메일 인증")
    fields:     str = Field(..., description="필요한 파라미터/필드 목록", example="userId, password, email")
    notes:      str = Field(default="", description="특이사항 / 추가 요구사항")
    reference:  str = Field(default="", description="기존 규격서에서 추출한 참고 텍스트")
    output_formats: List[OutputFormat] = Field(default=[OutputFormat.ALL])
    code_language:  CodeLanguage       = Field(default=CodeLanguage.PYTHON)
    author:         Optional[str]      = Field(default="SpecAutoAgent")


class SpecAutoJavaRequest(BaseModel):
    """Java 코드 분석 요청 모델 (Scenario A)"""
    java_code:     str = Field(..., description="Spring Controller .java 소스코드")
    reference_doc: str = Field(default="", description="기존 규격서에서 추출한 참고 텍스트")
    output_formats: List[OutputFormat] = Field(default=[OutputFormat.ALL])
    code_language:  CodeLanguage       = Field(default=CodeLanguage.JAVA)
    author:         Optional[str]      = Field(default="SpecAutoAgent")


# ─────────────────────────────────────────────
# Step 1: JSON Schema 모델 (AI 분석 결과)
# ─────────────────────────────────────────────

class SpecFieldSchema(BaseModel):
    """단일 필드 스키마 정의"""
    name:        str
    type:        str
    required:    bool          = True
    description: str           = ""
    example:     Any           = None
    format:      Optional[str] = None
    enum:        Optional[List[Any]] = None


class SpecErrorSchema(BaseModel):
    """에러 코드 정의"""
    code:        str
    description: str


class SpecApiSchema(BaseModel):
    """AI가 추론한 API 전체 스펙 (JSON Schema)"""
    api_name:      str
    endpoint:      str
    method:        HttpMethod
    description:   str
    version:       str                   = "v1"
    request:       List[SpecFieldSchema] = []
    response:      List[SpecFieldSchema] = []
    errors:        List[SpecErrorSchema] = []
    headers:       Dict[str, str]        = {}
    auth_required: bool                  = True
    tags:          List[str]             = []


# ─────────────────────────────────────────────
# Step 2: 생성 산출물 모델
# ─────────────────────────────────────────────

class SpecAutoAssets(BaseModel):
    """Step 2에서 생성된 산출물 묶음"""
    excel_path:       Optional[str]  = None
    word_path:        Optional[str]  = None
    postman_path:     Optional[str]  = None
    sample_code_path: Optional[str]  = None
    postman_json:     Optional[Dict] = None
    sample_code:      Optional[str]  = None


# ─────────────────────────────────────────────
# 최종 응답 모델
# ─────────────────────────────────────────────

class SpecAutoResponse(BaseModel):
    """SpecAutoAgent 최종 응답 모델"""
    success:    bool
    user_input: str
    api_schema: Optional[SpecApiSchema]  = None
    assets:     Optional[SpecAutoAssets] = None
    message:    str                      = ""
    error:      Optional[str]            = None


class SpecAutoHealthResponse(BaseModel):
    """헬스체크 응답"""
    status:  str = "ok"
    service: str = "SpecAutoAgent"
    version: str = "1.0.0"
