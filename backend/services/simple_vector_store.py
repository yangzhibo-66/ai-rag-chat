import numpy as np
import pickle
import os
from typing import List, Dict, Any
from config import settings
from pathlib import Path
from services.aliyun_embedding import AliyunEmbeddingFunction
from services.chunk_schema import normalize_chunks


class SimpleVectorStore:
    """简化的向量存储，使用numpy进行相似性搜索"""

    def __init__(self):
        # 使用阿里云百炼嵌入模型
        try:
            if settings.DASHSCOPE_API_KEY and settings.EMBEDDING_BASE_URL:
                self.embedding_func = AliyunEmbeddingFunction()
                self.dimension = 1024  # text-embedding-v4 的维度
                print("SimpleVectorStore: 使用阿里云百炼嵌入模型")
            else:
                # 如果没有配置阿里云，使用简单的模拟嵌入
                self.embedding_func = None
                self.dimension = 384
                print("SimpleVectorStore: 使用模拟嵌入模型")
        except Exception as e:
            print(f"SimpleVectorStore: 阿里云模型初始化失败，使用模拟模型: {e}")
            self.embedding_func = None
            self.dimension = 384

        self.storage_dir = Path("faiss_storage")
        self.storage_dir.mkdir(exist_ok=True)
        self.user_data = {}  # user_id -> {'embeddings': [], 'documents': []}
        self._load_all_data()

    def _get_user_data_path(self, user_id: int) -> str:
        """获取用户数据存储路径"""
        return self.storage_dir / f"user_{user_id}_data.pkl"

    def _load_all_data(self):
        """加载所有用户数据"""
        for file_path in self.storage_dir.glob("*_data.pkl"):
            try:
                user_id = int(file_path.stem.split('_')[1])
                self._load_user_data(user_id)
            except Exception as e:
                print(f"加载用户数据失败 {file_path}: {e}")

    def _load_user_data(self, user_id: int):
        """加载单个用户数据"""
        data_path = self._get_user_data_path(user_id)

        if data_path.exists():
            try:
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
                    self.user_data[user_id] = data
                print(f"已加载用户 {user_id} 的数据，包含 {len(data['embeddings'])} 个向量")
            except Exception as e:
                print(f"加载用户 {user_id} 数据失败: {e}")

    def _save_user_data(self, user_id: int):
        """保存用户数据"""
        if user_id not in self.user_data:
            return

        data_path = self._get_user_data_path(user_id)

        try:
            with open(data_path, 'wb') as f:
                pickle.dump(self.user_data[user_id], f)
        except Exception as e:
            print(f"保存用户 {user_id} 数据失败: {e}")

    def _get_or_create_user_data(self, user_id: int):
        """获取或创建用户数据"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'embeddings': [],
                'documents': []
            }
        return self.user_data[user_id]

    def _cosine_similarity(self, a, b) -> float:
        """计算余弦相似度"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def add_chunks(self, user_id: int, document_id: int, chunks, filename: str) -> None:
        """添加文档块到向量存储"""
        normalized = normalize_chunks(chunks)
        if not normalized:
            return

        user_data = self._get_or_create_user_data(user_id)

        # 生成嵌入向量
        if self.embedding_func:
            # 使用阿里云嵌入模型
            embeddings_list = self.embedding_func([c["content"] for c in normalized])
            embeddings = np.array(embeddings_list, dtype=np.float32)
        else:
            # 使用简单的模拟嵌入（用于测试）
            np.random.seed(42)  # 固定种子以便重现
            embeddings = np.random.rand(len(normalized), self.dimension).astype(np.float32)

        # 保存文档元数据和嵌入
        for i, (chunk, embedding) in enumerate(zip(normalized, embeddings)):
            doc_data = {
                "id": f"doc_{document_id}_chunk_{i}",
                "content": chunk["content"],
                "filename": filename,
                "document_id": str(document_id),
                "chunk_index": i,
                "page_number": chunk["page_number"],
                "section": chunk["section"],
                "kind": chunk["kind"],
            }
            user_data['documents'].append(doc_data)
            user_data['embeddings'].append(embedding)

        # 保存到磁盘
        self._save_user_data(user_id)
        print(f"用户 {user_id} 添加 {len(chunks)} 个文档块，总计 {len(user_data['embeddings'])} 个向量")

    def search(self, user_id: int, query: str, n_results: int = 5, document_ids: List[int] = None) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if user_id not in self.user_data:
            return []

        user_data = self.user_data[user_id]
        embeddings = user_data['embeddings']
        documents = user_data['documents']

        if document_ids:
            selected = {str(i) for i in document_ids}
            filtered = [(d, e) for d, e in zip(documents, embeddings) if d["document_id"] in selected]
            if not filtered:
                return []
            documents = [d for d, _ in filtered]
            embeddings = [e for _, e in filtered]

        if not embeddings:
            return []

        # 生成查询嵌入
        if self.embedding_func:
            # 使用阿里云嵌入模型
            query_embeddings = self.embedding_func([query])
            query_embedding = np.array(query_embeddings[0], dtype=np.float32)
        else:
            # 使用简单的模拟嵌入
            np.random.seed(hash(query) % 1000)  # 基于查询的哈希值
            query_embedding = np.random.rand(self.dimension).astype(np.float32)

        # 计算相似度
        similarities = []
        for i, embedding in enumerate(embeddings):
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((similarity, i))

        # 按相似度排序并获取前n_results个结果
        similarities.sort(reverse=True)
        top_results = similarities[:n_results]

        # 构建结果
        results = []
        for similarity, idx in top_results:
            doc = documents[idx]
            results.append({
                "content": doc["content"],
                "filename": doc["filename"],
                "document_id": doc["document_id"],
                "chunk_index": doc.get("chunk_index"),
                "page_number": doc.get("page_number"),
                "section": doc.get("section"),
                "kind": doc.get("kind") or "text",
                "similarity": float(similarity),
            })

        return results

    def delete_document(self, user_id: int, document_id: int) -> None:
        """删除文档"""
        if user_id not in self.user_data:
            return

        user_data = self.user_data[user_id]
        embeddings = user_data['embeddings']
        documents = user_data['documents']

        # 过滤出要保留的文档和嵌入
        docs_to_keep = []
        embeddings_to_keep = []

        for doc, embedding in zip(documents, embeddings):
            if doc["document_id"] != str(document_id):
                docs_to_keep.append(doc)
                embeddings_to_keep.append(embedding)

        docs_to_delete_count = len(documents) - len(docs_to_keep)

        if docs_to_delete_count == 0:
            return

        # 更新用户数据
        user_data['documents'] = docs_to_keep
        user_data['embeddings'] = embeddings_to_keep

        # 保存到磁盘
        self._save_user_data(user_id)

        print(f"用户 {user_id} 删除文档 {document_id}，移除了 {docs_to_delete_count} 个向量")


# 全局实例
simple_vector_store = SimpleVectorStore()
