from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 基本配置
    PROJECT_NAME: str = "AI RAG 知识库系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # JWT 配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # 数据库配置
    DATABASE_URL: str

    # 文件上传配置
    UPLOAD_DIR: str
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx", ".txt", ".md"}
    IMAGE_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    MAX_IMAGE_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # AI 配置（阿里云百炼 - OpenAI 兼容模式）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    DEFAULT_MODEL: str
    IMAGE_OCR_MODEL: Optional[str] = None

    # 阿里云百炼嵌入模型配置
    DASHSCOPE_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_MODEL: str

    # 向量数据库配置
    FAISS_DIR: str
    VECTOR_STORE_BACKEND: str = "chroma"
    VECTOR_STORE_FALLBACK: str = "mock"
    CHROMA_DIR: str = "chroma_db"
    CHROMA_COLLECTION: str = "rag_chunks"
    CHROMA_EMBEDDING_DIMENSION: int = 384

    # 文档解析 / 分块配置
    CHUNK_TARGET_SIZE: int = 500        # 分块目标长度（字符）
    CHUNK_MAX_SIZE: int = 900           # 单块上限（超出则二次切分）
    CHUNK_OVERLAP: int = 80             # 相邻文本块重叠字符数
    CHUNK_MIN_CHARS: int = 60           # 小于该长度的块尝试并入相邻块

    # 检索配置（混合检索 + 去噪）
    RAG_TOP_K: int = 5                          # 最终送入上下文的 chunk 数
    RAG_RECALL_K: int = 20                      # 向量 / 关键词各路召回数
    RAG_RELEVANCE_THRESHOLD: float = 0.35       # 语义相似度阈值，低于则过滤
    RAG_RERANK_ENABLED: bool = True             # 是否调用 Reranker（需 DASHSCOPE_API_KEY）
    RERANK_MODEL: str = "gte-rerank-v2"
    RERANK_BASE_URL: str = "https://dashscope.aliyuncs.com"
    KEYWORD_INDEX_DIR: str = "keyword_index"

    # PDF 解析配置
    RAG_OCR_MAX_PAGES: int = 30                 # 单文档最多 OCR 页/图数量（控制成本）
    RAG_SCANNED_PAGE_MIN_CHARS: int = 20        # 文字量低于该值视为扫描页候选
    RAG_IMAGE_MIN_AREA_RATIO: float = 0.15      # 页内图片面积占比超过该值才尝试 OCR

    # 生成质量闭环
    RAG_VERIFY_ENABLED: bool = True             # 生成后做一次答案-证据一致性自检
    RAG_QUERY_REWRITE_ENABLED: bool = True      # 检索为空时用 LLM 改写查询重试一次

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略 .env 中多余的字段


settings = Settings()