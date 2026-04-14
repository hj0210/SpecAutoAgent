# 🚀 SpecAutoAgent — 배포 가이드

> 자동 배포와 수동 배포 두 가지 방식을 모두 설명합니다.

---

## 📋 배포 파일 구조

| 파일 | 용도 |
|------|------|
| `docker-compose.yml` | **개발용** — 로컬 소스 코드로 직접 빌드 |
| `docker-compose.prod.yml` | **배포용** — Docker Hub 이미지 pull + Watchtower 자동화 |
| `.github/workflows/docker-publish.yml` | GitHub Actions CI/CD (push 시 자동 빌드 & Docker Hub 업로드) |

---

## 🤖 자동 배포 (권장)

### 흐름

```
코드 수정
  → git push (main 브랜치)
    → GitHub Actions 실행
      → Docker 이미지 빌드
        → Docker Hub 업로드 (chj0210/spec-auto-agent:latest)
          → Watchtower 감지 (5분 간격)
            → 컨테이너 자동 재시작 ✅
```

### 최초 1회 설정

```powershell
# .env 파일 준비
copy .env.example .env
# .env 열어서 OPENAI_API_KEY 등 입력

# Watchtower 포함 전체 실행
docker-compose -f docker-compose.prod.yml up -d
```

### 이후 배포

```powershell
# 코드 수정 후 push만 하면 끝
git add .
git commit -m "feat: 변경사항"
git push
# → 약 5~10분 후 자동 반영 (GitHub Actions 빌드 + Watchtower 감지)
```

### 현재 버전 확인

브라우저 우측 하단 뱃지 또는:
```powershell
curl http://localhost:8000/health
# {"status":"ok","service":"SpecAutoAgent","version":"1.2.0","build":"2026-04-10"}
```

---

## 🖐️ 수동 배포

### 언제 사용하나?
- Watchtower를 사용하지 않을 때
- GitHub Actions 완료 즉시 반영하고 싶을 때
- Watchtower 컨테이너를 끄고 직접 제어하고 싶을 때

### 방법 1 — Docker Hub 최신 이미지로 수동 업데이트

```powershell
# 1. GitHub Actions 완료 확인
# https://github.com/hj0210/SpecAutoAgent/actions → ✅ 초록불 확인

# 2. 최신 이미지 pull + 재시작
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# ※ PowerShell에서는 && 대신 ; 사용
docker-compose -f docker-compose.prod.yml pull; docker-compose -f docker-compose.prod.yml up -d
```

### 방법 2 — 로컬 소스로 직접 빌드

```powershell
# 코드 수정 후 바로 빌드 & 재시작 (Docker Hub 거치지 않음)
docker-compose up -d --build
```

### 방법 3 — 로컬 직접 실행 (Docker 없이)

```powershell
# 가상환경 활성화
venv\Scripts\activate

# 실행
uvicorn main:app --reload --port 8000
```

---

## ⏸️ Watchtower 끄기 (수동 배포만 사용)

`docker-compose.prod.yml` 에서 Watchtower 섹션 주석 처리:

```yaml
# watchtower:              ← 이 블록 전체 주석 처리
#   image: containrrr/watchtower
#   container_name: watchtower
#   volumes:
#     - /var/run/docker.sock:/var/run/docker.sock
#   command: --interval 300 spec-auto-agent
#   restart: unless-stopped
```

재시작:
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

이후 배포는 **방법 1 (수동 pull)** 로 진행.

---

## 🔁 Watchtower 다시 켜기

주석 제거 후:
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🐳 자주 쓰는 Docker 명령어

```powershell
# 실행 중인 컨테이너 확인
docker ps

# 로그 확인
docker logs spec-auto-agent
docker logs spec-auto-agent -f        # 실시간 로그

# 컨테이너 재시작
docker restart spec-auto-agent

# 전체 종료
docker-compose -f docker-compose.prod.yml down

# 이미지 목록
docker images | findstr spec-auto

# 이미지 강제 삭제 후 재pull
docker rmi chj0210/spec-auto-agent:latest
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## ⚠️ 주의사항

| 항목 | 내용 |
|------|------|
| `.env` 파일 | git에 절대 커밋 금지. `.gitignore`에 등록되어 있음 |
| `vector_db/` | ChromaDB 데이터. 볼륨 마운트로 컨테이너 재시작 후에도 유지 |
| `output/` | 생성 산출물. 볼륨 마운트로 영구 보존 |
| Docker Hub 토큰 | 반드시 **Read, Write, Delete** 권한으로 발급 |
| GitHub Secret | `DOCKERHUB_USERNAME=chj0210`, `DOCKERHUB_TOKEN` 설정 필요 |

---

## 🔍 배포 후 정상 확인 방법

```powershell
# 1. 컨테이너 상태
docker ps | findstr spec-auto

# 2. 헬스체크
curl http://localhost:8000/health

# 3. 브라우저 접속
# http://localhost:8000/ui → 우측 하단 버전 뱃지 확인
```
