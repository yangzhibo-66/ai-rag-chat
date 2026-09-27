from typing import Any, Dict, List

import faiss
import numpy as np
import pickle
from pathlib import Path

from config import settings
from services.chunk_schema import meta_from_storage, normalize_chunks
from services.aliyun_embedding import AliyunEmbeddingFunction


class FAISSVectorStore:
    """FAISS 向量存储：embedding 一次生成、随元数据持久化，查询零额外 API 调用。

    使用归一化向量 + 内积索引（IndexFlatIP），得分即余弦相似度。
    """

    def __init__(self):
        try:
            if settings.DASHSCOPE_API_KEY and settings.EMBEDDING_BASE_URL:
                self.embedding_func = AliyunEmbeddingFunction()
                self.dimension = self.embedding_func.dimension  # text-embedding-v4 的维度
                print("FAISS: 使用阿里云百炼嵌入模型")
            else:
                self.embedding_func = None
                self.dimension = 384
                print("FAISS: 未配置嵌入模型，使用模拟嵌入")
        except Exception as e:
            print(f"FAISS: 阿里云模型初始化失败，使用模拟模型: {e}")
            self.embedding_func = None
            self.dimension = 384
        self.index_map = {}  # user_id -> faiss_index
        self.data_map = {}   # user_id -> list of documents（含持久化的 embedding）
        self.storage_dir = Path("faiss_storage")
        self.storage_dir.mkdir(exist_ok=True)
        self._load_all_indices()

    def _get_user_storage_path(self, user_id: int) -> tuple:
        index_path = self.storage_dir / f"user_{user_id}_index.faiss"
        data_path = self.storage_dir / f"user_{user_id}_data.pkl"
        return index_path, data_path

    def _load_all_indices(self):
        for file_path in self.storage_dir.glob("*_index.faiss"):
            try:
                user_id = int(file_path.stem.split('_')[1])
                self._load_user_index(user_id)
            except Exception as e:
                print(f"加载用户索引失败 {file_path}: {e}")

    def _load_user_index(self, user_id: int):
        index_path, data_path = self._get_user_storage_path(user_id)

        if index_path.exists() and data_path.exists():
            try:
                index = faiss.read_index(str(index_path))
                self.index_map[user_id] = index

                with open(data_path, 'rb') as f:
                    self.data_map[user_id] = pickle.load(f)

                print(f"已加载用户 {user_id} 的FAISS索引，包含 {index.ntotal} 个向量")
            except Exception as e:
                print(f"加载用户 {user_id} 索引失败: {e}")

    def _save_user_index(self, user_id: int):
        if user_id not in self.index_map or user_id not in self.data_map:
            return

        index_path, data_path = self._get_user_storage_path(user_id)

        try:
            faiss.write_index(self.index_map[user_id], str(index_path))

            with open(data_path, 'wb') as f:
                pickle.dump(self.data_map[user_id], f)
        except Exception as e:
            print(f"保存用户 {user_id} 索引失败: {e}")

    def _get_or_create_index(self, user_id: int):
        if user_id not in self.index_map:
            index = faiss.IndexFlatIP(self.dimension)  # 归一化向量的内积 = 余弦相似度
            self.index_map[user_id] = index
            self.data_map[user_id] = []
        return self.index_map[user_id]

    def _embed(self, texts: List[str]) -> np.ndarray:
        if self.embedding_func:
            embeddings_list = self.embedding_func(texts)
        else:
            import hashlib

            embeddings_list = []
            for t in texts:
                digest = hashlib.sha256(t.encode("utf-8", errors="ignore")).digest()
                values = []
                while len(values) < self.dimension:
                    for b in digest:
                        values.append((b / 127.5) - 1.0)
                        if len(values) >= self.dimension:
                            break
                embeddings_list.append(values)
        arr = np.array(embeddings_list, dtype=np.float32)
        # 归一化，使内积即余弦相似度
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def add_chunks(self, user_id: int, document_id: int, chunks: List[Any], filename: str) -> None:
        normalized = normalize_chunks(chunks)
        if not normalized:
            return

        index = self._get_or_create_index(user_id)
        documents = self.data_map[user_id]
        if index.d != self.dimension:
            raise RuntimeError("FAISS 索引维度与当前嵌入模型不一致，请清理 faiss_storage 后重试")

        embeddings = self._embed([c["content"] for c in normalized])

        base_pos = index.ntotal
        index.add(embeddings)

        for i, c in enumerate(normalized):
            documents.append(
                {
                    "id": f"doc_{document_id}_chunk_{i}",
                    "content": c["content"],
                    "filename": filename,
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "page_number": c["page_number"],
                    "section": c["section"],
                    "kind": c["kind"],
                    "embedding_index": base_pos + i,
                }
            )

        self._save_user_index(user_id)
        print(f"用户 {user_id} 添加 {len(normalized)} 个文档块，总计 {index.ntotal} 个向量")

    def search(self, user_id: int, query: str, n_results: int = 5, document_ids: List[int] = None) -> List[Dict[str, Any]]:
        if user_id not in self.index_map or user_id not in self.data_map:
            return []

        index = self.index_map[user_id]
        all_documents = self.data_map[user_id]

        if index.ntotal == 0 or not all_documents:
            return []

        documents = all_documents
        if document_ids:
            selected = {str(i) for i in document_ids}
            documents = [d for d in all_documents if d["document_id"] in selected]

        if not documents:
            return []

        query_vector = self._embed([query])

        # 优先使用持久化的向量；历史数据缺失时跳过（不重复调用 embedding API）
        rows = []
        for doc in documents:
            pos = doc.get("embedding_index")
            if pos is None or pos < 0 or pos >= index.ntotal:
                continue
            score = float(index.reconstruct(pos) @ query_vector[0])
            rows.append((score, doc))
        if not rows:
            return []

        rows.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in rows[:n_results]:
            extra = meta_from_storage(doc.get("page_number"), doc.get("section"))
            results.append(
                {
                    "content": doc["content"],
                    "filename": doc["filename"],
                    "document_id": doc["document_id"],
                    "chunk_index": doc.get("chunk_index"),
                    "kind": doc.get("kind") or "text",
                    **extra,
                    "similarity": round(max(0.0, score), 4),
                }
            )
        return results

    def delete_document(self, user_id: int, document_id: int) -> None:
        if user_id not in self.data_map:
            return

        documents = self.data_map[user_id]
        docs_to_keep = [doc for doc in documents if doc["document_id"] != str(document_id)]
        docs_to_delete_count = len(documents) - len(docs_to_keep)
        if docs_to_delete_count == 0:
            return

        self.data_map[user_id] = docs_to_keep
        new_index = faiss.IndexFlatIP(self.dimension)

        old_index = self.index_map.get(user_id)
        vectors = []
        missing = False
        for doc in docs_to_keep:
            pos = doc.get("embedding_index")
            if old_index is None or pos is None or pos < 0 or pos >= old_index.ntotal:
                missing = True
                break
            vectors.append(old_index.reconstruct(pos))

        if docs_to_keep:
            if missing:
                embeddings = self._embed([doc["content"] for doc in docs_to_keep])
            else:
                embeddings = np.array(vectors, dtype=np.float32)
            new_index.add(embeddings)
            for i, doc in enumerate(docs_to_keep):
                doc["embedding_index"] = i

        self.index_map[user_id] = new_index
        self._save_user_index(user_id)

        print(f"用户 {user_id} 删除文档 {document_id}，移除了 {docs_to_delete_count} 个向量")


# 全局实例
faiss_vector_store = FAISSVectorStore()
