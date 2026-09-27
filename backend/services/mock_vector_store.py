import pickle
import os
from typing import Any, Dict, List
from pathlib import Path

from services.chunk_schema import normalize_chunks


class MockVectorStore:
    """模拟向量存储，用于测试和基本功能"""

    def __init__(self):
        print("MockVectorStore: 使用模拟向量存储")
        self.storage_dir = Path("faiss_storage")
        self.storage_dir.mkdir(exist_ok=True)
        self.user_data = {}  # user_id -> list of documents
        self._load_all_data()

    def _get_user_data_path(self, user_id: int) -> str:
        """获取用户数据存储路径"""
        return self.storage_dir / f"user_{user_id}_mock_data.pkl"

    def _load_all_data(self):
        """加载所有用户数据"""
        for file_path in self.storage_dir.glob("*_mock_data.pkl"):
            try:
                # 从文件名中提取用户ID，格式为 user_{id}_mock_data.pkl
                filename = file_path.stem
                if '_' in filename:
                    parts = filename.split('_')
                    if len(parts) >= 3:
                        user_id = int(parts[1])
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
                print(f"已加载用户 {user_id} 的数据，包含 {len(data)} 个文档")
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
            self.user_data[user_id] = []
        return self.user_data[user_id]

    def _simple_similarity(self, query: str, text: str) -> float:
        """简单的文本相似度计算"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        intersection = query_words.intersection(text_words)
        return len(intersection) / len(query_words)

    def add_chunks(self, user_id: int, document_id: int, chunks, filename: str) -> None:
        """添加文档块到向量存储"""
        normalized = normalize_chunks(chunks)
        if not normalized:
            return

        user_data = self._get_or_create_user_data(user_id)

        # 保存文档元数据
        for i, chunk in enumerate(normalized):
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
            user_data.append(doc_data)

        # 保存到磁盘
        self._save_user_data(user_id)
        print(f"用户 {user_id} 添加 {len(chunks)} 个文档块，总计 {len(user_data)} 个文档")

    def search(self, user_id: int, query: str, n_results: int = 5, document_ids: List[int] = None) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if user_id not in self.user_data:
            return []

        user_data = self.user_data[user_id]

        if document_ids:
            selected = {str(i) for i in document_ids}
            user_data = [d for d in user_data if d["document_id"] in selected]

        if not user_data:
            return []

        # 计算相似度
        similarities = []
        for i, doc in enumerate(user_data):
            similarity = self._simple_similarity(query, doc["content"])
            similarities.append((similarity, i))

        # 按相似度排序并获取前n_results个结果
        similarities.sort(reverse=True)
        top_results = similarities[:n_results]

        # 构建结果
        results = []
        for similarity, idx in top_results:
            doc = user_data[idx].copy()
            doc["similarity"] = similarity
            # 只返回需要的字段
            results.append({
                "content": doc["content"],
                "filename": doc["filename"],
                "document_id": doc["document_id"],
                "chunk_index": doc.get("chunk_index"),
                "page_number": doc.get("page_number"),
                "section": doc.get("section"),
                "kind": doc.get("kind") or "text",
                "similarity": similarity,
            })

        return results

    def delete_document(self, user_id: int, document_id: int) -> None:
        """删除文档"""
        if user_id not in self.user_data:
            return

        user_data = self.user_data[user_id]

        # 过滤出要保留的文档
        docs_to_keep = [
            doc for doc in user_data
            if doc["document_id"] != str(document_id)
        ]

        docs_to_delete_count = len(user_data) - len(docs_to_keep)

        if docs_to_delete_count == 0:
            return

        # 更新用户数据
        self.user_data[user_id] = docs_to_keep

        # 保存到磁盘
        self._save_user_data(user_id)

        print(f"用户 {user_id} 删除文档 {document_id}，移除了 {docs_to_delete_count} 个文档")


# 全局实例
mock_vector_store = MockVectorStore()
