"""按用户维护的 BM25 关键词索引，与向量检索做 RRF 融合（混合检索）。

索引持久化为 pickle（每用户一个文件），内存中保存分词后的语料并重建 BM25。
分词针对中英混排：英文/数字按词，中文按二元组（bigram），无需额外分词依赖。
"""
import logging
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List

from config import settings
from services.chunk_schema import normalize_chunks

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> List[str]:
    """英文按词、中文按字，再把相邻中文两两组成 bigram。"""
    tokens: List[str] = []
    latin: List[str] = []
    cjk: List[str] = []
    for m in _TOKEN_RE.finditer(text or ""):
        t = m.group(0)
        if t.isdigit() or t.isascii():
            latin.append(t.lower())
        else:
            cjk.append(t)
    tokens.extend(latin)
    tokens.extend(f"{a}{b}" for a, b in zip(cjk, cjk[1:]))
    if cjk and not cjk[1:]:
        tokens.append(cjk[0])
    return tokens


class _FallbackBM25:
    """rank-bm25 不可用时的极简 TF-IDF 替代，接口兼容 score。"""

    def __init__(self, corpus_tokens: List[List[str]]):
        self.corpus = corpus_tokens
        self.df: Dict[str, int] = {}
        for tokens in corpus_tokens:
            for t in set(tokens):
                self.df[t] = self.df.get(t, 0) + 1
        self.n = max(1, len(corpus_tokens))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        scores = []
        for tokens in self.corpus:
            counter: Dict[str, int] = {}
            for t in tokens:
                counter[t] = counter.get(t, 0) + 1
            score = 0.0
            for qt in query_tokens:
                if qt in counter:
                    score += counter[qt] * (1 + self.df.get(qt, 0))
            scores.append(score)
        return scores


class KeywordIndex:
    def __init__(self):
        self.storage_dir = Path(settings.KEYWORD_INDEX_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # user_id -> {doc_id(str): {"chunks": [dict], "tokens": [List[str]]}}
        self.user_data: Dict[int, Dict[str, Dict[str, Any]]] = {}
        self._bm25_cache: Dict[int, Any] = {}
        self._load_all()

    def _path(self, user_id: int) -> Path:
        return self.storage_dir / f"user_{user_id}_keyword.pkl"

    def _load_all(self):
        for file_path in self.storage_dir.glob("*_keyword.pkl"):
            try:
                user_id = int(file_path.stem.split("_")[1])
                with open(file_path, "rb") as f:
                    self.user_data[user_id] = pickle.load(f)
            except Exception as e:
                logger.warning("加载用户 %s 关键词索引失败: %s", file_path.name, e)

    def _save(self, user_id: int):
        try:
            with open(self._path(user_id), "wb") as f:
                pickle.dump(self.user_data.get(user_id, {}), f)
        except Exception as e:
            logger.warning("保存用户 %s 关键词索引失败: %s", user_id, e)
        self._bm25_cache.pop(user_id, None)

    def _get_bm25(self, user_id: int):
        if user_id in self._bm25_cache:
            return self._bm25_cache[user_id]
        docs = self.user_data.get(user_id) or {}
        if not docs:
            return None
        corpus_tokens: List[List[str]] = []
        for entry in docs.values():
            corpus_tokens.extend(entry["tokens"])
        try:
            from rank_bm25 import BM25Okapi

            bm25 = BM25Okapi(corpus_tokens)
        except Exception:
            bm25 = _FallbackBM25(corpus_tokens)
        self._bm25_cache[user_id] = bm25
        return bm25

    def _flat_entries(self, user_id: int, document_ids: List[int] | None):
        docs = self.user_data.get(user_id) or {}
        selected = {str(i) for i in document_ids} if document_ids else None
        flat: List[Dict[str, Any]] = []
        for doc_id in sorted(docs.keys()):
            if selected is not None and doc_id not in selected:
                continue
            entry = docs[doc_id]
            for chunk, tokens in zip(entry["chunks"], entry["tokens"]):
                flat.append({"doc_id": doc_id, "chunk": chunk, "tokens": tokens})
        return flat

    def add_document(self, user_id: int, document_id: int, chunks: List[Any], filename: str) -> None:
        normalized = normalize_chunks(chunks)
        if not normalized:
            return
        docs = self.user_data.setdefault(user_id, {})
        docs[str(document_id)] = {
            "chunks": [
                {
                    "content": c["content"],
                    "filename": filename,
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "page_number": c["page_number"],
                    "section": c["section"],
                    "kind": c["kind"],
                }
                for i, c in enumerate(normalized)
            ],
            "tokens": [tokenize(c["content"]) for c in normalized],
        }
        self._save(user_id)

    def delete_document(self, user_id: int, document_id: int) -> None:
        docs = self.user_data.get(user_id)
        if not docs or str(document_id) not in docs:
            return
        docs.pop(str(document_id), None)
        self._save(user_id)

    def search(
        self,
        user_id: int,
        query: str,
        top_n: int = 10,
        document_ids: List[int] | None = None,
    ) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        bm25 = self._get_bm25(user_id)
        if bm25 is None:
            return []

        # BM25 在该用户的全部语料上打分，再按 doc 过滤映射回结果
        docs = self.user_data.get(user_id) or {}
        selected = {str(i) for i in document_ids} if document_ids else None

        flat: List[Dict[str, Any]] = []
        for doc_id in sorted(docs.keys()):
            if selected is not None and doc_id not in selected:
                continue
            entry = docs[doc_id]
            for chunk, tokens in zip(entry["chunks"], entry["tokens"]):
                flat.append({"chunk": chunk, "doc_id": doc_id})
        if not flat:
            return []

        scores = bm25.get_scores(query_tokens)
        ranked = sorted(zip(scores, range(len(flat))), key=lambda x: x[0], reverse=True)[:top_n]

        results = []
        for score, idx in ranked:
            if score <= 0:
                continue
            item = dict(flat[idx]["chunk"])
            item["keyword_score"] = round(float(score), 4)
            results.append(item)
        return results


keyword_index = KeywordIndex()
