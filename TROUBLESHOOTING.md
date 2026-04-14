# SpecAutoAgent — 트러블슈팅 히스토리

> 발생했던 오류와 해결 방법을 기록합니다.
> 동일한 문제가 반복되지 않도록 원인 / 분석 / 해결방안 형식으로 정리합니다.

---

## #1. OpenAI API 사용 한도 초과 (429 RateLimitError)

| 항목 | 내용 |
|------|------|
| **증상** | 규격서 생성 시 500 오류, 로그에 `RateLimitError` |
| **원인** | `.env`의 `OPENAI_API_KEY`가 무료 한도 소진 또는 잘못된 키 |
| **분석** | OpenAI 무료 계정은 월 사용량 한도 존재. 만료된 키나 소진 키는 429 반환 |
| **해결** | 유료 키 새로 발급 → `.env`의 `OPENAI_API_KEY` 교체 |
| **예방** | `.env.example`에 실제 키 절대 넣지 말 것. 키 소진 전 플랫폼에서 알림 설정 |

---

## #2. .env.example에 실제 API 키 노출

| 항목 | 내용 |
|------|------|
| **증상** | `.env.example` 파일에 실제 `OPENAI_API_KEY` 값이 들어있음 |
| **원인** | `.env` 수정 후 `.env.example`도 함께 수정하면서 실제 키가 포함됨 |
| **분석** | `.env.example`은 GitHub에 올라가는 파일 — 실제 키가 들어있으면 공개 노출 위험. 다행히 해당 버전은 GitHub에 커밋되기 전에 발견 |
| **해결** | `.env.example`의 실제 키를 `sk-...` 플레이스홀더로 교체. 기존 키 즉시 폐기 후 신규 발급 |
| **예방** | `.env.example`에는 절대 실제 값 입력 금지. 값 자리는 `<your-key>` 또는 `sk-...` 형식으로만 작성 |

```
# .env.example 올바른 예시
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=
```

---

## #3. GitHub Actions Docker Hub Push 권한 오류

| 항목 | 내용 |
|------|------|
| **증상** | `ERROR: unauthorized: access token has insufficient scopes` |
| **원인** | Docker Hub 액세스 토큰이 **Read-only** 권한으로 생성됨 |
| **분석** | GitHub Actions에서 이미지를 push하려면 **Read, Write, Delete** 권한 필요 |
| **해결** | Docker Hub → Settings → Security → 기존 토큰 삭제 → 새 토큰 발급 (권한: Read, Write, Delete) → GitHub Secret `DOCKERHUB_TOKEN` 업데이트 |
| **예방** | Docker Hub 토큰 생성 시 권한 반드시 **Read, Write, Delete** 선택 |

---

## #4. PowerShell에서 `&&` 명령어 오류

| 항목 | 내용 |
|------|------|
| **증상** | `'&&' 토큰은 이 버전에서 올바른 문 구분 기호가 아닙니다` |
| **원인** | `&&`는 Linux/Mac 쉘 문법. Windows PowerShell에서는 지원 안 됨 |
| **분석** | PowerShell은 `;`를 명령어 구분자로 사용 |
| **해결** | `&&` 대신 `;` 사용 |

```powershell
# ❌ 안됨 (Linux 문법)
docker-compose pull && docker-compose up -d

# ✅ PowerShell
docker-compose pull; docker-compose up -d
```

---

## #5. docker-compose pull 해도 최신 이미지 미반영

| 항목 | 내용 |
|------|------|
| **증상** | `docker-compose pull` 실행해도 새 코드가 반영되지 않음 |
| **원인** | `docker-compose.yml`은 `build: .` 방식 — Docker Hub에서 pull하지 않고 로컬 소스를 빌드 |
| **분석** | `docker-compose.yml` (개발용) vs `docker-compose.prod.yml` (배포용, Docker Hub 이미지 사용) 두 파일이 분리되어 있음 |
| **해결** | Docker Hub 이미지 사용 시 prod 파일 명시, 또는 로컬 빌드 강제 |

```powershell
# Docker Hub 최신 이미지로 실행 (prod)
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 로컬 소스로 직접 빌드 (가장 확실)
docker-compose up -d --build
```

---

## #6. 브라우저 캐시로 구버전 UI 표시

| 항목 | 내용 |
|------|------|
| **증상** | Docker 재시작 후에도 브라우저에서 구버전 UI가 보임 |
| **원인** | 브라우저가 HTML/JS를 캐싱하고 있음. 시크릿 모드에서도 동일 증상 가능 |
| **분석** | 서버는 이미 새 버전이나 브라우저가 캐시된 파일을 먼저 사용 |
| **해결** | `Ctrl + Shift + R` 강제 새로고침. 또는 F12 → Network → Disable cache 체크 후 새로고침 |
| **예방** | 우측 하단 버전 뱃지(`v1.x.x · yyyy-mm-dd`) 확인으로 현재 실행 버전 식별 가능 |

---

## #7. Gemini API `response_format` 지원 안 함 (404)

| 항목 | 내용 |
|------|------|
| **증상** | Gemini 사용 시 `NotFoundError` 또는 `404` 오류 |
| **원인** | Gemini OpenAI 호환 엔드포인트는 `response_format: {"type": "json_object"}` 파라미터 미지원 |
| **분석** | OpenAI 전용 파라미터를 Gemini에도 동일하게 전송하면 오류 발생 |
| **해결** | `is_gemini` 플래그로 분기 처리 — Gemini일 때 `response_format` 파라미터 제외. 대신 프롬프트로 JSON 출력 강제 |

```python
if not is_gemini:
    create_kwargs["response_format"] = {"type": "json_object"}
```

---

## #8. RAG 인덱싱 시 pandoc 없음 오류

| 항목 | 내용 |
|------|------|
| **증상** | 규격서 DB 탭에서 docx 업로드 시 `❌ 오류: pandoc이 설치되어 있지 않습니다` |
| **원인** | Docker 컨테이너 내부에 pandoc이 없음. RAG 인덱서가 docx → 텍스트 변환 시 pandoc 사용 |
| **분석** | 로컬 PC에 pandoc이 설치되어 있어도 Docker 컨테이너는 별개의 환경이라 내부에 별도 설치 필요 |
| **해결** | `Dockerfile`에 pandoc 설치 추가 후 이미지 재빌드 |

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pandoc \
    && rm -rf /var/lib/apt/lists/*
```

---

## 버전 확인 방법

서버 실행 후 우측 하단 뱃지 또는 `/health` 엔드포인트:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"SpecAutoAgent","version":"1.2.0","build":"2026-04-10"}
```
