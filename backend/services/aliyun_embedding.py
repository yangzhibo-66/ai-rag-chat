import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union

import requests

from config import settings


class AliyunEmbeddingFunction:
    """阿里云百炼 OpenAI 兼容 embedding 客户端，按批请求并并行发送以降低耗时。"""

    BATCH_SIZE = 10   # DashScope text-embedding 系列单请求最大输入条数
    MAX_WORKERS = 4   # 多批并行度
    MAX_RETRIES = 2

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL
        self.model = settings.EMBEDDING_MODEL

        if not self.api_key or not self.base_url:
            raise ValueError("阿里云百炼 API 配置不完整")

    @property
    def dimension(self) -> int:
        return 1024

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """为文本列表生成嵌入向量（自动分批、批间并行、失败重试）"""
        if isinstance(input, str):
            input = [input]
        input = [t if isinstance(t, str) else str(t) for t in input]
        if not input:
            return []

        batches = [input[i : i + self.BATCH_SIZE] for i in range(0, len(input), self.BATCH_SIZE)]
        if len(batches) == 1:
            return self._get_batch_embeddings(batches[0])

        with ThreadPoolExecutor(max_workers=min(self.MAX_WORKERS, len(batches))) as ex:
            results = list(ex.map(self._get_batch_embeddings, batches))
        return [vec for batch in results for vec in batch]

    def _get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {"model": self.model, "input": texts}

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
                if response.status_code != 200:
                    # 透出服务端错误详情（如 Arrearage 欠费、参数错误），便于快速定位
                    try:
                        detail = response.json().get("error", {}).get("message") or response.text[:200]
                    except Exception:
                        detail = response.text[:200]
                    raise RuntimeError(f"embedding API {response.status_code}: {detail}")
                result = response.json()
                rows = result.get("data") or []
                if len(rows) != len(texts):
                    raise ValueError(f"API 返回条数不符: 期望 {len(texts)}, 实际 {len(rows)}")
                rows.sort(key=lambda r: r.get("index", 0))
                return [r["embedding"] for r in rows]
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"获取嵌入向量失败（重试 {self.MAX_RETRIES} 次）: {last_error}")
