# ─────────────────────────────────────────────
# SpecAutoAgent - FastAPI Dockerfile
# ─────────────────────────────────────────────

FROM python:3.11-slim

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 (python-docx + RAG 인덱싱용 pandoc 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 산출물 저장 디렉토리 생성
RUN mkdir -p spec_auto_agent/output

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
