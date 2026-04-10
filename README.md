# 🤖 SpecAutoAgent

> **Natural Language → API Spec, Docs & Code. Automated.**
> LLM 기반 API 연동규격서 & 샘플 코드 자동 생성 AI 에이전트
> `Python · FastAPI · OpenAI GPT-4o · Docker`

---

## ✨ 한 줄 요약

**시나리오 A — 기존 Java 코드 → 규격서 자동 생성**
```
입력: Spring Controller .java 파일 업로드

출력:
  ├── 📊 API 연동 규격서 (Excel + Word)   ← 실제 코드와 100% 일치
  ├── ☕ Java(Spring Boot) 샘플 코드
  └── 📬 Postman Collection
```

**시나리오 B — 자연어 입력 → 규격서 & 코드 신규 생성**
```
입력: "회원가입 API 만들어줘. 아이디, 비번, 이메일이 필요하고 중복 체크 기능도 있어야 해."

출력:
  ├── 📊 API 연동 규격서 (Excel + Word)
  ├── 🐍 Python(FastAPI) 또는 ☕ Java(Spring Boot) 샘플 코드
  └── 📬 Postman Collection (Import 즉시 테스트 가능)
```

---

## 🗺️ 전체 로드맵

```
Phase 1 ✅  로컬 단독 실행 (현재)
            FastAPI + GPT-4o + 규격서 생성
                │
Phase 2 🔜  Docker Compose 통합 실행 (진행 중)
            FastAPI 컨테이너화
                │
Phase 3 📋  Spring Boot RAG 모듈 추가
            pgvector 유사 규격서 검색 → 생성 품질 향상
                │
Phase 4 📋  Azure 클라우드 배포
            Azure Functions + Blob Storage + DevOps Pipeline
```

---

## 🏗️ 아키텍처

**Phase 1~2 (현재)**
```
[Web UI]
    ↓
[FastAPI - Python :8000]
    ├── Scenario A: Java 파일 업로드 → Regex+GPT-4o 분석
    └── Scenario B: 자연어 입력 → GPT-4o 분석
                          ↓
                    [SpecApiSchema]
                          ↓
          ┌───────────────┼───────────────┐
    [Excel/Word]    [Postman]        [샘플 코드]
```

**Phase 3 (예정) — Spring Boot RAG 추가**
```
[Web UI]
    ↓
[FastAPI - Python :8000]  ──→  [Spring Boot RAG :8001]  ──→  [pgvector :5432]
    │                                    │
    │                          유사 규격서 패턴 3~5개 반환
    │                                    │
    └────────────────→ [GPT-4o] ←────────┘
                            ↓
                    [Excel/Word/Postman/Code]
```

---

## 📁 프로젝트 구조

```
SpecAutoAgent/
├── main.py                                  # FastAPI 진입점
├── Dockerfile                               # 컨테이너 빌드
├── docker-compose.yml                       # 서비스 통합 실행
├── .dockerignore
├── requirements.txt
├── .env.example                             # 환경변수 템플릿
├── .env                                     # 실제 환경변수 (git 제외)
├── .gitignore
│
├── templates/
│   └── index.html                           # Web UI (4개 탭)
│
└── spec_auto_agent/
    ├── core/
    │   ├── spec_auto_client.py              # OpenAI / Azure / Gemini 클라이언트 팩토리
    │   ├── spec_auto_analyzer.py            # 자연어 → SpecApiSchema (GPT-4o)
    │   ├── spec_auto_java_parser.py         # Java 코드 → SpecApiSchema (Regex+GPT-4o)
    │   ├── spec_auto_doc_gen.py             # Excel / Word 규격서 생성
    │   ├── spec_auto_code_gen.py            # Python / Java 샘플 코드 생성
    │   └── spec_auto_postman.py             # Postman Collection v2.1 생성
    ├── models/
    │   └── spec_auto_models.py              # Pydantic 데이터 모델 전체
    └── output/                              # 생성 산출물 저장 (git 제외)
```

---

## ⚡ 실행 방법

### 방법 1 — Docker (권장)

```bash
# .env 파일 준비
cp .env.example .env
# OPENAI_API_KEY 입력 후 저장

# 빌드 & 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up --build -d

# 종료
docker-compose down
```

### 방법 2 — 로컬 직접 실행

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

→ **http://localhost:8000/ui** 접속

---

## 🌐 URL 구조

| URL | 설명 |
|---|---|
| `http://localhost:8000/ui` | **Web UI** (메인 사용 화면) |
| `http://localhost:8000/docs` | Swagger API 문서 |
| `http://localhost:8000/health` | 헬스체크 |

---

## 🔑 환경변수

`.env.example` 복사 후 값 입력:

```env
# AI 엔진 선택 (우선순위: Azure > Gemini > OpenAI)
USE_AZURE=false
USE_GEMINI=false

# OpenAI (현재 사용)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Google Gemini (무료 티어 — 하루 1,500회)
# GEMINI_API_KEY=
# GEMINI_MODEL=gemini-2.0-flash

# Azure OpenAI (Phase 4 배포 시)
# AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
# AZURE_OPENAI_KEY=
# AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

## 🔄 컴포넌트별 역할

| 컴포넌트 | 역할 |
|---|---|
| `SpecAutoClient` | `USE_AZURE` / `USE_GEMINI` 값으로 AI 엔진 자동 선택 |
| `SpecAutoJavaParser` | Regex 1차 파싱 + GPT-4o 심층 분석 → SpecApiSchema |
| `SpecAutoAnalyzer` | 자연어 → SpecApiSchema (GPT-4o) |
| `SpecAutoDocGen` | Excel / Word 규격서 생성 (openpyxl, python-docx) |
| `SpecAutoCodeGen` | Python / Java 샘플 코드 생성 (GPT-4o) |
| `SpecAutoPostman` | Postman Collection v2.1 JSON 조립 |

### Java 파싱 지원 어노테이션

| 유형 | 어노테이션 |
|---|---|
| HTTP 매핑 | `@RequestMapping` `@GetMapping` `@PostMapping` `@PutMapping` `@PatchMapping` `@DeleteMapping` |
| 파라미터 | `@RequestBody` `@RequestParam` `@PathVariable` |
| 검증 | `@NotNull` `@NotBlank` `@NotEmpty` `@Size` `@Min` `@Max` `@Valid` `@Pattern` `@Email` |
| 예외 | `@ExceptionHandler` `@ResponseStatus` |

---

## 🧪 주요 API 엔드포인트

| 엔드포인트 | 설명 |
|---|---|
| `POST /api/spec-auto/generate` | 자연어 단일 입력 → 규격서·코드 생성 |
| `POST /api/spec-auto/generate-structured` | 구조화 입력(목적/기능/필드) → 규격서·코드 생성 |
| `POST /api/spec-auto/parse-java` | Java 코드 분석 → 규격서·코드 생성 |
| `POST /api/spec-auto/parse-reference` | 기존 Excel/Word 규격서 → 텍스트 추출 |
| `GET  /api/spec-auto/download/{filename}` | 생성 산출물 다운로드 |

---

## 📋 Phase별 구현 현황

| Phase | 내용 | 상태 |
|---|---|---|
| Phase 1 | FastAPI + GPT-4o 로컬 실행 | ✅ 완료 |
| Phase 1 | Scenario A (Java 코드 분석) | ✅ 완료 |
| Phase 1 | Scenario B (자연어 입력) | ✅ 완료 |
| Phase 1 | Excel / Word / Postman / 코드 생성 | ✅ 완료 |
| Phase 1 | 기존 규격서 참고 (reference 업로드) | ✅ 완료 |
| Phase 2 | Dockerfile 작성 | ✅ 완료 |
| Phase 2 | docker-compose.yml 작성 | ✅ 완료 |
| Phase 3 | Spring Boot RAG 서비스 개발 | 📋 예정 |
| Phase 3 | pgvector 유사 규격서 검색 | 📋 예정 |
| Phase 3 | FastAPI ↔ Spring Boot 연동 | 📋 예정 |
| Phase 4 | Azure Functions 배포 | 📋 예정 |
| Phase 4 | Azure Blob Storage 연동 | 📋 예정 |
| Phase 4 | KT 표준 템플릿 파일 연동 | 📋 예정 |
| Phase 4 | Git 변경 감지 → 자동 트리거 | 📋 예정 |

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| AI 엔진 | OpenAI GPT-4o / Azure OpenAI / Google Gemini (`.env` 전환) |
| 백엔드 | Python 3.11+, FastAPI, Uvicorn |
| 데이터 검증 | Pydantic v2 |
| 문서 생성 | openpyxl (Excel), python-docx (Word) |
| 테스트 에셋 | Postman Collection v2.1 |
| 컨테이너 | Docker, Docker Compose |
| RAG (예정) | Spring Boot 3.x, Spring AI, pgvector |
| 클라우드 (예정) | Azure Functions, Blob Storage, DevOps Pipeline |
