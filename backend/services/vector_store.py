from config import settings


def _load_store(name: str):
    if name == "chroma":
        from services.chroma_vector_store import chroma_vector_store

        return chroma_vector_store
    if name == "simple":
        from services.simple_vector_store import simple_vector_store

        return simple_vector_store
    if name == "faiss":
        from services.faiss_vector_store import faiss_vector_store

        return faiss_vector_store
    from services.mock_vector_store import mock_vector_store

    return mock_vector_store


backend = (settings.VECTOR_STORE_BACKEND or "chroma").lower()
fallback = (settings.VECTOR_STORE_FALLBACK or "mock").lower()

try:
    vector_store = _load_store(backend)
    print(f"vector_store backend={backend}")
except Exception as e:
    vector_store = _load_store(fallback)
    print(f"vector_store backend={backend} 初始化失败，已回退到 {fallback}: {e}。请检查 chromadb/numpy 依赖是否完整")
