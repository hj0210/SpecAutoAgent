"""
rag_searcher.py
ChromaDB에서 유사 규격서 청크를 검색하고
GPT 프롬프트에 컨텍스트로 주입하는 모듈

사용 흐름:
  사용자 입력 (자연어) → 임베딩 → ChromaDB 코사인 유사도 검색
  → Top-K 청크 → 프롬프트 컨텍스트로 조립 → GPT에 전달
"""
import logging
from typing import List, Dict, Optional

from spec_auto_agent.core.rag_indexer import (
    get_chroma_client,
    embed_texts,
    CHROMA_COLLECTION,
)

logger = logging.getLogger(__name__)


def search_similar_specs(
    query: str,
    top_k: int = 3,
    doc_name_filter: Optional[str] = None,
) -> List[Dict]:
    """
    쿼리와 유사한 규격서 청크 검색

    Args:
        query: 검색할 자연어 또는 API 설명
        top_k: 반환할 최대 청크 수
        doc_name_filter: 특정 문서만 검색 (None이면 전체)

    Returns:
        [{"text": str, "metadata": dict, "distance": float}, ...]
    """
    try:
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)

        # 컬렉션이 비어있으면 빈 결과 반환
        count = collection.count()
        if count == 0:
            logger.info("[RAG] ChromaDB가 비어있습니다. 규격서를 먼저 업로드하세요.")
            return []

        # 쿼리 임베딩
        query_embedding = embed_texts([query])[0]

        # 검색 조건
        where_filter = {"doc_name": doc_name_filter} if doc_name_filter else None

        # ChromaDB 유사도 검색
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # 결과 정리
        chunks = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append({
                "text": doc,
                "metadata": meta or {},
                "distance": round(dist, 4),
                "similarity": round(1 - dist, 4),  # 코사인 유사도 (1에 가까울수록 유사)
            })

        logger.info(f"[RAG] '{query[:50]}...' → {len(chunks)}개 청크 검색 완료")
        return chunks

    except Exception as e:
        logger.warning(f"[RAG] 검색 중 오류 (규격서 없이 계속 진행): {e}")
        return []


def build_rag_context(
    query: str,
    top_k: int = 3,
    doc_name_filter: Optional[str] = None,
) -> str:
    """
    GPT 프롬프트에 삽입할 RAG 컨텍스트 문자열 조립

    Returns:
        "=== 참고 규격서 (RAG) ===\n[섹션명]\n...내용..." 형식의 문자열
        (검색 결과 없으면 빈 문자열)
    """
    chunks = search_similar_specs(query, top_k=top_k, doc_name_filter=doc_name_filter)
    if not chunks:
        return ""

    lines = ["=== 참고 규격서 (RAG 검색 결과) ==="]
    lines.append("아래는 기존 연동규격서에서 이 요청과 가장 유사한 섹션들입니다.")
    lines.append("이 내용을 참고하여 동일한 형식과 수준으로 규격서를 작성하세요.\n")

    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        doc_name = meta.get("doc_name", "")
        section  = meta.get("section", "")
        api_id   = meta.get("api_id", "")
        sim      = chunk["similarity"]

        lines.append(f"--- 참고 {i}: [{doc_name}] {section} (유사도: {sim:.0%}) ---")
        if api_id:
            lines.append(f"I/F ID: {api_id}")
        lines.append(chunk["text"][:800])  # 너무 길면 자름
        lines.append("")

    return "\n".join(lines)


def get_rag_stats() -> Dict:
    """ChromaDB 현황 통계"""
    try:
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
        total = collection.count()

        # 문서별 청크 수
        all_items = collection.get(include=["metadatas"])
        doc_map: Dict[str, int] = {}
        for meta in all_items.get("metadatas", []):
            if meta:
                name = meta.get("doc_name", "unknown")
                doc_map[name] = doc_map.get(name, 0) + 1

        return {
            "total_chunks": total,
            "documents": [{"doc_name": k, "chunks": v} for k, v in doc_map.items()],
            "collection": CHROMA_COLLECTION,
        }
    except Exception as e:
        return {"total_chunks": 0, "documents": [], "error": str(e)}
