"""
rag_indexer.py
연동규격서 docx를 읽어서 API별로 청킹 후 ChromaDB에 저장하는 모듈

흐름:
  docx 업로드 → pandoc으로 텍스트 추출 → API 섹션별 청킹
  → OpenAI Embedding → ChromaDB 저장
"""
import os
import re
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ChromaDB + OpenAI 임포트 (런타임에 체크)
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed. Run: pip install chromadb")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ChromaDB 저장 경로
CHROMA_DB_PATH = Path(__file__).parent.parent / "vector_db"
CHROMA_COLLECTION = "spec_documents"


def get_chroma_client():
    """ChromaDB 클라이언트 반환 (영구 저장)"""
    if not CHROMA_AVAILABLE:
        raise RuntimeError("chromadb 패키지가 설치되어 있지 않습니다. pip install chromadb 실행 필요")
    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DB_PATH))


def get_embedding_client():
    """OpenAI or Gemini 임베딩 클라이언트 반환"""
    use_azure  = os.getenv("USE_AZURE", "false").lower() == "true"
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

    if use_azure:
        from openai import AzureOpenAI
        return AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        ), "text-embedding-ada-002"
    elif use_gemini:
        # Gemini는 임베딩 모델 별도 사용 (OpenAI 호환)
        client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return client, "text-embedding-004"
    else:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY")), "text-embedding-3-small"


def extract_text_from_docx(docx_path: str) -> str:
    """pandoc으로 docx → 마크다운 텍스트 추출"""
    try:
        result = subprocess.run(
            ["pandoc", docx_path, "-t", "plain", "--wrap=none"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"pandoc 변환 실패: {result.stderr}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("pandoc이 설치되어 있지 않습니다. https://pandoc.org/installing.html")


def chunk_spec_document(text: str, doc_name: str) -> List[Dict]:
    """
    규격서 텍스트를 API 섹션별로 청킹

    청킹 전략:
    1. API 상세 섹션 헤더로 분리 (\[오퍼\], \[수집\] 등)
    2. 너무 길면 500자 단위로 추가 분할
    3. 메타데이터에 문서명, 섹션명, API ID 포함
    """
    chunks = []

    # 문서 메타 섹션 (앞 부분 - 개요, 용어, 프로토콜)
    meta_section = _extract_meta_section(text)
    if meta_section:
        chunks.append({
            "id": _make_id(doc_name, "meta"),
            "text": meta_section[:2000],
            "metadata": {
                "doc_name": doc_name,
                "section": "문서개요",
                "api_id": "",
                "api_name": "시스템 인터페이스 개요",
                "chunk_type": "meta",
            }
        })

    # API 상세 섹션 분리 패턴
    # "[오퍼] 일반 캠페인 조회 (PC, MOBILE)" 같은 헤더
    api_section_pattern = re.compile(
        r'(#{1,4}\s*[\[\[【\(]?(?:오퍼|수집|Collect|Offer|collect|offer)[^\n]*\n)',
        re.IGNORECASE
    )

    # 섹션 헤더 기반 분리
    parts = re.split(r'(\n#{1,4}\s+(?:\[.*?\]|\(.*?\)|[가-힣A-Za-z].{3,60})\n)', text)

    current_section = ""
    current_header = ""

    for part in parts:
        if re.match(r'\n#{1,4}\s+', part):
            # 이전 섹션 저장
            if current_section and len(current_section.strip()) > 100:
                sub_chunks = _split_long_text(
                    current_section.strip(), current_header, doc_name
                )
                chunks.extend(sub_chunks)
            current_header = part.strip().lstrip('#').strip()
            current_section = part
        else:
            current_section += part

    # 마지막 섹션
    if current_section and len(current_section.strip()) > 100:
        sub_chunks = _split_long_text(
            current_section.strip(), current_header, doc_name
        )
        chunks.extend(sub_chunks)

    # API별 청킹이 너무 적으면 (문서 구조가 다른 경우) 단순 분할
    if len(chunks) <= 2:
        chunks = _fallback_chunk(text, doc_name)

    logger.info(f"'{doc_name}' → {len(chunks)}개 청크 생성")
    return chunks


def _extract_meta_section(text: str) -> str:
    """문서 앞부분 메타 정보 추출"""
    lines = text.split('\n')
    meta_lines = []
    for i, line in enumerate(lines[:100]):
        meta_lines.append(line)
        # 목차나 본문 시작 감지
        if re.search(r'(인터페이스 개요|인터페이스 정보|인터페이스 명세)', line):
            break
    return '\n'.join(meta_lines)


def _split_long_text(text: str, header: str, doc_name: str, max_chars: int = 1500) -> List[Dict]:
    """긴 텍스트를 max_chars 단위로 분할 청킹"""
    # API ID 추출 시도
    api_id_match = re.search(r'I/F ID[^\w]*([\w.]+)', text)
    api_id = api_id_match.group(1) if api_id_match else ""

    chunks = []
    if len(text) <= max_chars:
        chunks.append({
            "id": _make_id(doc_name, header),
            "text": text,
            "metadata": {
                "doc_name": doc_name,
                "section": header,
                "api_id": api_id,
                "api_name": header,
                "chunk_type": "api_spec",
            }
        })
    else:
        # max_chars 단위로 분할 (문단 기준으로 자름)
        paragraphs = text.split('\n\n')
        current = ""
        part_idx = 0
        for para in paragraphs:
            if len(current) + len(para) > max_chars and current:
                chunks.append({
                    "id": _make_id(doc_name, f"{header}_p{part_idx}"),
                    "text": current.strip(),
                    "metadata": {
                        "doc_name": doc_name,
                        "section": header,
                        "api_id": api_id,
                        "api_name": header,
                        "chunk_type": "api_spec",
                        "part": part_idx,
                    }
                })
                part_idx += 1
                current = para
            else:
                current += "\n\n" + para
        if current.strip():
            chunks.append({
                "id": _make_id(doc_name, f"{header}_p{part_idx}"),
                "text": current.strip(),
                "metadata": {
                    "doc_name": doc_name,
                    "section": header,
                    "api_id": api_id,
                    "api_name": header,
                    "chunk_type": "api_spec",
                    "part": part_idx,
                }
            })
    return chunks


def _fallback_chunk(text: str, doc_name: str, chunk_size: int = 1000) -> List[Dict]:
    """문서 구조 파악 안 될 때 단순 슬라이딩 윈도우 청킹"""
    chunks = []
    step = chunk_size // 2  # 50% 오버랩
    for i, start in enumerate(range(0, len(text), step)):
        chunk_text = text[start:start + chunk_size]
        if len(chunk_text) < 100:
            break
        chunks.append({
            "id": _make_id(doc_name, f"chunk_{i}"),
            "text": chunk_text,
            "metadata": {
                "doc_name": doc_name,
                "section": f"chunk_{i}",
                "api_id": "",
                "api_name": "",
                "chunk_type": "sliding_window",
            }
        })
    return chunks


def _make_id(doc_name: str, section: str) -> str:
    """청크 고유 ID 생성"""
    raw = f"{doc_name}::{section}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """텍스트 목록을 임베딩 벡터로 변환"""
    client, model = get_embedding_client()

    # 최대 토큰 초과 방지 - 2000자로 truncate
    texts = [t[:2000] for t in texts]

    try:
        response = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
    except Exception as e:
        raise RuntimeError(f"임베딩 생성 실패: {str(e)}")


def index_document(docx_path: str, doc_name: Optional[str] = None) -> Dict:
    """
    메인 진입점: docx → 청킹 → 임베딩 → ChromaDB 저장

    Returns:
        {"doc_name": str, "chunks_count": int, "status": "ok"}
    """
    if doc_name is None:
        doc_name = Path(docx_path).stem

    logger.info(f"[RAG] 인덱싱 시작: {doc_name}")

    # 1. 텍스트 추출
    text = extract_text_from_docx(docx_path)

    # 2. 청킹
    chunks = chunk_spec_document(text, doc_name)
    if not chunks:
        raise RuntimeError("청킹 결과가 없습니다. 문서 내용을 확인하세요.")

    # 3. 임베딩 (배치 처리 - 한 번에 최대 100개)
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embed_texts(texts)
        all_embeddings.extend(embeddings)

    # 4. ChromaDB 저장
    chroma_client = get_chroma_client()
    collection = chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}  # 코사인 유사도
    )

    # 기존 같은 문서 삭제 후 재저장 (업데이트 지원)
    try:
        existing = collection.get(where={"doc_name": doc_name})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(f"[RAG] 기존 '{doc_name}' 청크 {len(existing['ids'])}개 삭제")
    except Exception:
        pass

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=all_embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    logger.info(f"[RAG] 인덱싱 완료: {doc_name} → {len(chunks)}개 청크")
    return {
        "doc_name": doc_name,
        "chunks_count": len(chunks),
        "status": "ok",
    }


def list_indexed_documents() -> List[Dict]:
    """ChromaDB에 저장된 문서 목록 조회"""
    try:
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
        all_items = collection.get()

        # 문서명 기준으로 집계
        doc_map: Dict[str, int] = {}
        for meta in all_items.get("metadatas", []):
            if meta:
                name = meta.get("doc_name", "unknown")
                doc_map[name] = doc_map.get(name, 0) + 1

        return [{"doc_name": k, "chunks": v} for k, v in doc_map.items()]
    except Exception as e:
        return []


def delete_document(doc_name: str) -> Dict:
    """특정 문서의 청크 전체 삭제"""
    chroma_client = get_chroma_client()
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    existing = collection.get(where={"doc_name": doc_name})
    if not existing["ids"]:
        return {"status": "not_found", "doc_name": doc_name}
    collection.delete(ids=existing["ids"])
    return {"status": "deleted", "doc_name": doc_name, "deleted_chunks": len(existing["ids"])}
