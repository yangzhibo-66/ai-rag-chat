"""检索门面：混合检索（向量 + BM25 关键词）→ RRF 融合 → 可选 Reranker → 相关性阈值。

对上层（chat / documents / 评估脚本）暴露统一接口：
    add_document / delete_document / search

search 流程：
    1. 双路召回（语义向量 + BM25 关键词），RRF 融合排序；
    2. 可选 Reranker 精排（失败自动降级为 RRF 排序）；
    3. 语义相似度低于阈值的 chunk 被过滤（检索去噪）；
    4. 若一条都没召回，可选地用 LLM 改写查询后重试一次。
"""
import logging
from typing import Any, Dict, List, Optional

import requests

from config import settings
from services.keyword_index import keyword_index
from services.vector_store import vector_store

logger = logging.getLogger(__name__)

_RRF_K = 60  # RRF 平滑常数


def add_document(user_id: int, document_id: int, chunks: List[Any], filename: str) -> None:
    """写入两个索引：向量库（语义）+ 关键词索引（BM25）。"""
    vector_store.add_chunks(user_id, document_id, chunks, filename)
    keyword_index.add_document(user_id, document_id, chunks, filename)


def delete_document(user_id: int, document_id: int) -> None:
    vector_store.delete_document(user_id, document_id)
    keyword_index.delete_document(user_id, document_id)


def search(
    user_id: int,
    query: str,
    document_ids: Optional[List[int]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """混合检索：返回带 page_number / section / similarity 的 chunk 列表。"""
    top_k = top_k or settings.RAG_TOP_K

    results = _hybrid_search(user_id, query, document_ids=document_ids, top_k=top_k)

    # 空结果时用 LLM 换一种问法重试一次（改写失败则原样返回）
    if not results and settings.RAG_QUERY_REWRITE_ENABLED:
        try:
            from services.ai_service import rewrite_query

            rewritten = rewrite_query(query)
            if rewritten and rewritten.strip() and rewritten.strip() != query.strip():
                logger.info("检索为空，使用改写查询重试: %s", rewritten)
                results = _hybrid_search(user_id, rewritten.strip(), document_ids=document_ids, top_k=top_k)
        except Exception as e:
            logger.warning("查询改写重试失败: %s", e)

    return results


def _hybrid_search(
    user_id: int,
    query: str,
    document_ids: Optional[List[int]],
    top_k: int,
) -> List[Dict[str, Any]]:
    recall_k = settings.RAG_RECALL_K

    vec_hits = []
    kw_hits = []
    try:
        vec_hits = vector_store.search(user_id, query, n_results=recall_k, document_ids=document_ids)
    except Exception as e:
        logger.warning("向量检索失败: %s", e)
    try:
        kw_hits = keyword_index.search(user_id, query, top_n=recall_k, document_ids=document_ids)
    except Exception as e:
        logger.warning("关键词检索失败: %s", e)

    if not vec_hits and not kw_hits:
        return []

    candidates = _fuse(vec_hits, kw_hits)

    # Reranker 精排（对召回候选）
    if settings.RAG_RERANK_ENABLED and settings.DASHSCOPE_API_KEY and len(candidates) > 1:
        try:
            rerank_order = _rerank(query, [c["hit"]["content"] for c in candidates[:recall_k]])
            candidates = _apply_rerank_order(candidates, rerank_order)
        except Exception as e:
            logger.warning("Reranker 失败，使用 RRF 排序: %s", e)

    # 相关性阈值过滤：语义得分缺失（纯关键词命中）时保留，由 RRF 排名兜底
    results = []
    for c in candidates:
        sim = c["hit"].get("similarity")
        if sim is not None and sim < settings.RAG_RELEVANCE_THRESHOLD:
            continue
        results.append(c["hit"])
        if len(results) >= top_k:
            break
    return results


def _fuse(vec_hits: List[Dict[str, Any]], kw_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """RRF 融合两路召回结果。"""

    def _key(hit: Dict[str, Any]) -> str:
        return f"{hit.get('document_id')}:{hit.get('chunk_index')}"

    fused: Dict[str, Dict[str, Any]] = {}
    for rank, hit in enumerate(vec_hits):
        k = _key(hit)
        entry = fused.setdefault(k, {"hit": hit, "rrf": 0.0})
        entry["rrf"] += 1.0 / (_RRF_K + rank + 1)
    for rank, hit in enumerate(kw_hits):
        k = _key(hit)
        entry = fused.setdefault(k, {"hit": hit, "rrf": 0.0})
        if entry["hit"].get("similarity") is None:
            # 关键词命中的补充语义字段（若向量路未召回该 chunk）
            for field in ("filename", "content", "page_number", "section", "kind"):
                entry["hit"].setdefault(field, hit.get(field))
        entry["rrf"] += 1.0 / (_RRF_K + rank + 1)

    return sorted(fused.values(), key=lambda x: x["rrf"], reverse=True)


# ------------------------------------------------------------------ #
# Reranker（阿里云 DashScope gte-rerank，失败向上抛出由调用方降级）      #
# ------------------------------------------------------------------ #

def _rerank(query: str, documents: List[str]) -> List[int]:
    url = f"{settings.RERANK_BASE_URL}/api/v1/services/rerank/text-rerank/text-rerank"
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.RERANK_MODEL,
        "input": {"query": query, "documents": documents},
        "parameters": {"return_documents": False, "top_n": len(documents)},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("output", {}).get("results") or []
    return [int(r["index"]) for r in results]


def _apply_rerank_order(candidates: List[Dict[str, Any]], order: List[int]) -> List[Dict[str, Any]]:
    if not order:
        return candidates
    top = [candidates[i] for i in order if 0 <= i < len(candidates)]
    rest = [c for i, c in enumerate(candidates) if i not in set(order)]
    return top + rest
