import base64
from pathlib import Path
from typing import Any

import requests

from config import settings


def _extract_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return ""


def extract_image_text(file_path: str, file_type: str | None = None) -> str:
    image_path = Path(file_path)
    if not image_path.exists():
        raise ValueError("图片文件不存在")

    img_bytes = image_path.read_bytes()
    if not img_bytes:
        raise ValueError("图片文件为空")

    mime = (file_type or "").strip().lower()
    if not mime.startswith("image/"):
        ext = image_path.suffix.lower().lstrip(".")
        mime = f"image/{'jpeg' if ext == 'jpg' else ext}" if ext else "image/png"

    return extract_image_text_from_bytes(img_bytes, mime)


def extract_image_text_from_bytes(img_bytes: bytes, mime: str = "image/png") -> str:
    """对图片字节流执行 OCR / 多模态识别，供 PDF 扫描页渲染后复用。"""
    api_key = settings.OPENAI_API_KEY
    base_url = settings.OPENAI_BASE_URL
    model = settings.IMAGE_OCR_MODEL or settings.DEFAULT_MODEL

    if not api_key or not base_url:
        raise ValueError("未配置图片 OCR 所需的 OPENAI_API_KEY 或 OPENAI_BASE_URL")
    if not img_bytes:
        raise ValueError("图片文件为空")

    image_b64 = base64.b64encode(img_bytes).decode("utf-8")
    image_url = f"data:{mime};base64,{image_b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个图像OCR与信息抽取助手。请尽量完整提取图片中的文字；如果几乎没有文字，请描述关键可见信息。输出纯文本，不要使用Markdown。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请提取这张图片中的可检索信息。"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 1500,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"OCR 响应为空: {data}")

    message = choices[0].get("message") or {}
    text = _extract_content_text(message.get("content"))
    if not text.strip():
        raise ValueError("OCR 未提取到可用内容")

    return text.strip()
