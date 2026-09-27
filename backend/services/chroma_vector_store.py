import hashlib
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from services.chunk_schema import meta_from_storage, meta_to_storage, normalize_chunks


class ChromaVectorStore:
    def __init__(self):
        self.storage_dir = Path(settings.CHROMA_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 优先使用真实语义 embedding（阿里云百炼），未配置时降级为哈希模拟向量
        self.embedding_func = None
        self.dimension = settings.CHROMA_EMBEDDING_DIMENSION
        if settings.DASHSCOPE_API_KEY and settings.EMBEDDING_BASE_URL:
            try:
                from services.aliyun_embedding import AliyunEmbeddingFunction

                self.embedding_func = AliyunEmbeddingFunction()
                self.dimension = self.embedding_func.dimension
                print(f"ChromaVectorStore: 使用阿里云百炼嵌入模型 {settings.EMBEDDING_MODEL}")
            except Exception as e:
                print(f"ChromaVectorStore: 嵌入模型初始化失败，回退哈希模拟向量: {e}")

        self.client = chromadb.PersistentClient(
            path=str(self.storage_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # 集合名带维度与距离空间，避免历史哈希向量 / L2 集合与新语义向量混用
        collection_name = f"{settings.CHROMA_COLLECTION}_{self.dimension}_cosine"
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"ChromaVectorStore: 使用持久化目录 {self.storage_dir}, 集合 {collection_name}")

    def _embedding_for_text(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        values: List[float] = []
        while len(values) < self.dimension:
            for b in digest:
                values.append((b / 127.5) - 1.0)
                if len(values) >= self.dimension:
                    break
        return values

    def _embeddings_for_texts(self, texts: List[str]) -> List[List[float]]:
        if self.embedding_func:
            return self.embedding_func(texts)
        return [self._embedding_for_text(t) for t in texts]

    def add_chunks(self, user_id: int, document_id: int, chunks: List[Any], filename: str) -> None:
        normalized = normalize_chunks(chunks)
        if not normalized:
            return

        texts = [c["content"] for c in normalized]
        ids = [f"u{user_id}_d{document_id}_c{i}" for i in range(len(normalized))]
        embeddings = self._embeddings_for_texts(texts)
        metadatas = []
        for i, c in enumerate(normalized):
            meta = {
                "user_id": user_id,
                "document_id": str(document_id),
                "filename": filename,
                "chunk_index": i,
                "kind": c["kind"],
            }
            meta.update(meta_to_storage(c["page_number"], c["section"]))
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, user_id: int, query: str, n_results: int = 5, document_ids: List[int] = None) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        count = self.collection.count()
        if count == 0:
            return []

        where: Dict[str, Any] = {"user_id": user_id}
        if document_ids:
            where = {
                "$and": [
                    {"user_id": user_id},
                    {"document_id": {"$in": [str(i) for i in document_ids]}},
                ]
            }

        query_embedding = self._embeddings_for_texts([query])[0]
        n_results = min(n_results, count)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = result.get("documents", [[]])
        metas = result.get("metadatas", [[]])
        distances = result.get("distances", [[]])
        if not docs or not metas:
            return []

        rows = []
        for index, (content, meta) in enumerate(zip(docs[0], metas[0])):
            distance = distances[0][index] if distances and distances[0] and index < len(distances[0]) else None
            extra = meta_from_storage(meta.get("page_number"), meta.get("section"))
            rows.append(
                {
                    "content": content,
                    "filename": meta.get("filename", ""),
                    "document_id": str(meta.get("document_id", "")),
                    "chunk_index": meta.get("chunk_index"),
                    "kind": meta.get("kind") or "text",
                    **extra,
                    "similarity": round(max(0.0, 1 - float(distance)), 4) if distance is not None else None,
                }
            )
        return rows

    def delete_document(self, user_id: int, document_id: int) -> None:
        self.collection.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"document_id": str(document_id)},
                ]
            }
        )


chroma_vector_store = ChromaVectorStore()
