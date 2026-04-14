# 🤖 SpecAutoAgent

> **Natural Language → API Spec, Docs & Code. Automated.**
> LLM 기반 API 연동규격서 & 샘플 코드 자동 생성 AI 에이전트
> `Python · FastAPI · OpenAI GPT-4o · ChromaDB · Docker`

---

## ✨ 주요 기능

**시나리오 A — Java 코드 → 규격서 자동 생성**
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

**시나리오 C — RAG 규격서 DB (Phase 2 신규)**
```
입력: 기존 연동규격서 .docx 업로드 → ChromaDB 인덱싱

효과:
  └── 이후 규격서 생성 시 유사 기존 규격서를 자동 참조 → 품질 향상
```

---

## 🗺️ 전체 로드맵

```
Phase 1 ✅  로컬 단독 실행
            FastAPI + GPT-4o + 규격서/코드/Postman 생성
            Scenario A (Java 분석) + Scenario B (자연어)
                │
Phase 2 ✅  Docker + GitHub Actions CI/CD + RAG (현재)
            컨테이너화, Docker Hub 자동 배포
            ChromaDB 기반 규격서 벡터 검색 및 생성 자동 참조
                │
Phase 3 📋  Spring Boot RAG 모듈
            pgvector 고도화, Spring AI 연동
                │
Phase 4 📋  Azure 클라우드 배포
            Azure Functions + Blob Storage + DevOps Pipeline
```

---

## 🏗️ 아키텍처

**Phase 1~2 (현재)**
```
[Web UI — 5개 탭]
    │
    ├── 📋 구조화 입력  ──┐
    ├── ✏️ 자유 입력    ──┤──→ [FastAPI :8000]
    ├── ☕ 코드 분석    ──┤         │
    ├── 🧠 규격서 DB   ──┘         ├── RAG 검색 (ChromaDB)
    └── ⚡ 예시                     │       ↑ 인덱싱된 기존 규격서
                                    │
                              [SpecApiSchema]
                                    │
                      ┌─────────────┼──────────────┐
                [Excel/Word]   [Postman]      [샘플 코드]
```

**자동 배포 흐름**
```
git push → GitHub Actions → Docker Hub (chj0210/spec-auto-agent:latest)
                                  ↓
                         Watchtower (5분 감지) → 자동 재시작
```

---

## 📁 프로젝트 구조

```
SpecAutoAgent/
├── main.py                          # FastAPI 진입점 + 전체 라우터
├── Dockerfile                       # 컨테이너 빌드 (pandoc 포함)
├── docker-compose.yml               # 로컬 개발용 (소스 직접 빌드)
├── docker-compose.prod.yml          # 배포용 (Docker Hub 이미지 + Watchtower)
├── requirements.txt                 # Python 패키지 (chromadb 포함)
├── .env.example                     # 환경변수 템플릿 (실제 값 없음)
├── .env                             # 실제 환경변수 (git 제외)
├── .gitignore
├── .dockerignore
├── README.md                        # 이 파일
├── DEPLOYMENT.md                    # 배포 프로세스 상세 가이드
├── TROUBLESHOOTING.md               # 오류 히스토리 및 해결방법
│
├── .github/
│   └── workflows/
│       └── docker-publish.yml       # GitHub Actions CI/CD
│
├── templates/
│   └── index.html                   # Web UI (5개 탭)
│
└── spec_auto_agent/
    ├── core/
    │   ├── spec_auto_client.py      # AI 엔진 팩토리 (OpenAI/Azure/Gemini)
    │   ├── spec_auto_analyzer.py    # 자연어 → SpecApiSchema + RAG 자동 주입
    │   ├── spec_auto_java_parser.py # Java 코드 → SpecApiSchema (Regex+GPT)
    │   ├── spec_auto_doc_gen.py     # Excel / Word 규격서 생성
    │   ├── spec_auto_code_gen.py    # Python / Java 샘플 코드 생성
    │   ├── spec_auto_postman.py     # Postman Collection v2.1 생성
    │   ├── rag_indexer.py           # docx → 청킹 → 임베딩 → ChromaDB 저장
    │   └── rag_searcher.py          # ChromaDB 유사도 검색 → GPT 컨텍스트 조립
    ├── models/
    │   └── spec_auto_models.py      # Pydantic 모델 전체 정의
    ├── output/                      # 생성 산출물 (git/docker 제외, 볼륨 마운트)
    └── vector_db/                   # ChromaDB 데이터 (git/docker 제외, 볼륨 마운트)
```

---

## ⚡ 빠른 시작

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 열어서 OPENAI_API_KEY 입력
```

### 2. 실행 (Docker 권장)

```bash
# 배포용 (Docker Hub 이미지)
docker-compose -f docker-compose.prod.yml up -d

# 개발용 (로컬 소스 빌드)
docker-compose up --build -d
```

→ **http://localhost:8000/ui** 접속

> 상세 배포 가이드는 **[DEPLOYMENT.md](./DEPLOYMENT.md)** 참조

---

## 🌐 URL

| URL | 설명 |
|-----|------|
| `http://localhost:8000/ui` | Web UI 메인 |
| `http://localhost:8000/docs` | Swagger API 문서 |
| `http://localhost:8000/health` | 헬스체크 + 버전 확인 |

---

## 🔑 환경변수

```env
# AI 엔진 선택 (우선순위: Azure > Gemini > OpenAI)
USE_AZURE=false
USE_GEMINI=false

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Google Gemini (무료 — 하루 1,500회)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# Azure OpenAI (Phase 4)
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

---

## 🧠 RAG 사용법

1. **🧠 규격서 DB 탭** → `.docx` 연동규격서 업로드 → 인덱싱
2. 이후 **📋 구조화 입력 / ✏️ 자유 입력** 탭에서 규격서 생성 시 자동 참조
3. **검색 테스트**: 검색어 입력 → 우측 패널에 유사 규격서 카드로 표시

---

## 🧪 API 엔드포인트

| 엔드포인트 | 설명 |
|------------|------|
| `POST /api/spec-auto/generate` | 자연어 단일 입력 → 규격서·코드 생성 |
| `POST /api/spec-auto/generate-structured` | 구조화 입력 → 규격서·코드 생성 |
| `POST /api/spec-auto/parse-java` | Java 코드 분석 → 규격서·코드 생성 |
| `POST /api/spec-auto/parse-reference` | Excel/Word → 텍스트 추출 (1회용 참조) |
| `GET  /api/spec-auto/download/{filename}` | 생성 파일 다운로드 |
| `POST /api/rag/index-doc` | docx 업로드 → ChromaDB 인덱싱 |
| `POST /api/rag/search` | 유사 규격서 검색 |
| `GET  /api/rag/stats` | 인덱싱 현황 |
| `GET  /api/rag/documents` | 인덱싱 문서 목록 |
| `DELETE /api/rag/documents/{name}` | 문서 삭제 |

---

## 🔄 컴포넌트 역할

| 컴포넌트 | 역할 |
|----------|------|
| `SpecAutoClient` | `.env` 값으로 OpenAI / Azure / Gemini 자동 선택 |
| `SpecAutoAnalyzer` | 자연어 → SpecApiSchema, RAG 컨텍스트 자동 주입 |
| `SpecAutoJavaParser` | Regex 1차 + GPT-4o 심층 분석 하이브리드 |
| `SpecAutoDocGen` | openpyxl(Excel) + python-docx(Word) 규격서 생성 |
| `SpecAutoCodeGen` | Python/Java 샘플 코드 GPT 생성 |
| `SpecAutoPostman` | Postman Collection v2.1 JSON 조립 |
| `RagIndexer` | docx → pandoc 추출 → 청킹 → 임베딩 → ChromaDB |
| `RagSearcher` | 쿼리 임베딩 → 코사인 유사도 검색 → GPT 프롬프트 조립 |

---

## 📋 구현 현황

| Phase | 항목 | 상태 |
|-------|------|------|
| 1 | FastAPI 서버 + Web UI | ✅ |
| 1 | Scenario A — Java 코드 분석 | ✅ |
| 1 | Scenario B — 자연어/구조화 입력 | ✅ |
| 1 | Excel / Word / Postman / 코드 생성 | ✅ |
| 1 | AI 엔진 전환 (OpenAI/Gemini/Azure) | ✅ |
| 2 | Docker 컨테이너화 | ✅ |
| 2 | GitHub Actions CI/CD | ✅ |
| 2 | Docker Hub 자동 배포 | ✅ |
| 2 | Watchtower 자동 재시작 | ✅ |
| 2 | ChromaDB RAG 인덱싱/검색 | ✅ |
| 2 | RAG 컨텍스트 생성 자동 주입 | ✅ |
| 3 | Spring Boot RAG 서비스 | 📋 예정 |
| 3 | pgvector 고도화 | 📋 예정 |
| 4 | Azure 배포 | 📋 예정 |
| 4 | KT 표준 Excel 템플릿 적용 | 📋 예정 |

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| AI 엔진 | OpenAI GPT-4o / Azure OpenAI / Google Gemini |
| 백엔드 | Python 3.11, FastAPI, Uvicorn |
| RAG | ChromaDB, OpenAI Embeddings (text-embedding-3-small) |
| 문서 추출 | pandoc (docx → text) |
| 문서 생성 | openpyxl (Excel), python-docx (Word) |
| 컨테이너 | Docker, Docker Compose, Watchtower |
| CI/CD | GitHub Actions → Docker Hub |
| RAG 고도화 (예정) | Spring Boot 3.x, Spring AI, pgvector |
| 클라우드 (예정) | Azure Functions, Blob Storage |
