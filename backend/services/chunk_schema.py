"""chunk 统一结构：所有向量库后端共用。

chunk 可以是 str（旧接口）或 dict：
    {"content": str, "page_number": int|None, "section": str|None, "kind": str}
"""
from typing import Any, Dict, List


def normalize_chunks(chunks: List[Any]) -> List[Dict[str, Any]]:
    """把 str / dict 混合列表统一为带元数据的 dict 列表。"""
    normalized: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            content = str(chunk.get("content") or "").strip()
            normalized.append(
                {
                    "content": content,
                    "page_number": chunk.get("page_number"),
                    "section": chunk.get("section"),
                    "kind": chunk.get("kind") or "text",
                }
            )
        else:
            normalized.append(
                {
                    "content": str(chunk or "").strip(),
                    "page_number": None,
                    "section": None,
                    "kind": "text",
                }
            )
    return [c for c in normalized if c["content"]]


def meta_to_storage(page_number, section) -> Dict[str, Any]:
    """转成向量库可存储的标量元数据（Chroma 不接受 None）。"""
    return {
        "page_number": int(page_number) if page_number is not None else -1,
        "section": str(section) if section else "",
    }


def meta_from_storage(page_number, section):
    return {
        "page_number": page_number if isinstance(page_number, int) and page_number >= 0 else None,
        "section": section if section else None,
    }
