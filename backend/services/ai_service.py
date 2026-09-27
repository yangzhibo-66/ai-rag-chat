from typing import AsyncIterator, Optional
import asyncio
import requests
import json
from config import settings
import logging

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """你是一个专业的 AI 知识库助手，基于用户上传的文档回答问题。

规则：
1. 仅根据「参考文档」中的内容回答，禁止编造或补充文档中没有的信息。
2. 回答中引用的关键结论必须标注来源，格式如 [来源: 文件名 · 第3页] 或 [来源: 文件名 · 概览小节]；没有页码的文档只写文件名。
3. 如果参考文档与问题无关或不足以回答，直接说明"当前文档中未找到足够的相关内容"，不要猜测。
4. 使用 Markdown 格式让回答更易读（标题、加粗、列表、代码块等）。
5. 默认使用中文回答，除非用户明确用英文提问。"""

RAG_RETRY_SUFFIX = """

【修正要求】上一次回答与参考文档的一致性不足。请严格只依据参考文档重新回答：
- 只陈述参考文档能支持的内容，逐条标注来源；
- 证据不足的部分明确写"文档中未提及"，不要推测。"""

FREE_SYSTEM_PROMPT = """你是一个专业、可靠的 AI 助手。

规则：
1. 基于你的通用知识与用户提供的信息回答。
2. 不要伪造事实；不确定时请明确说明不确定。
3. 使用 Markdown 格式让回答更易读（标题、加粗、列表、代码块等）。
4. 默认使用中文回答，除非用户明确用英文提问。"""


def _source_label(chunk: dict) -> str:
    name = (chunk.get("filename") or "").strip()
    page = chunk.get("page_number")
    section = (chunk.get("section") or "").strip()
    label = name or "未知文档"
    if page:
        label += f" · 第{page}页"
    elif section:
        label += f" · {section}"
    return label


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "（未检索到与问题相关的文档内容）"

    image_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    parts = []
    for c in chunks:
        name = c.get("filename", "")
        prefix = "图片来源" if name.lower().endswith(image_exts) else "来源"
        parts.append(f"【{prefix}：{_source_label(c)}】\n{c['content']}")
    return "\n\n---\n\n".join(parts)


async def stream_response(
    message: str,
    retrieved_chunks: list[dict],
    history: list[dict],
    chat_mode: str = "free",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    retry_strict: bool = False,
) -> AsyncIterator[str]:
    """使用阿里云百炼 OpenAI 兼容 API 流式响应"""

    # 使用配置或传入的参数
    effective_key = api_key or settings.OPENAI_API_KEY
    effective_model = model or settings.DEFAULT_MODEL
    effective_base_url = base_url or settings.OPENAI_BASE_URL

    # 检查配置
    if not effective_key:
        yield "（未配置 API Key，请在设置页面填写或在服务器 .env 文件中设置后重启服务）"
        return

    if not effective_base_url:
        yield "（未配置 API Base URL，请在设置页面填写或在服务器 .env 文件中设置）"
        return

    if chat_mode == "rag_selected":
        context = _build_context(retrieved_chunks)
        system = f"{RAG_SYSTEM_PROMPT}{RAG_RETRY_SUFFIX if retry_strict else ''}\n\n参考文档内容：\n{context}"
    else:
        system = FREE_SYSTEM_PROMPT

    # 构建消息历史
    openai_messages = [{"role": "system", "content": system}]
    for h in history[-10:]:
        openai_messages.append({"role": h["role"], "content": h["content"]})
    openai_messages.append({"role": "user", "content": message})

    try:
        # 直接调用阿里云百炼 API
        url = f"{effective_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {effective_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": effective_model,
            "messages": openai_messages,
            "max_tokens": 2048,
            # RAG 回答需要贴合证据，温度低于自由对话
            "temperature": 0.3 if chat_mode == "rag_selected" else 0.7,
            "stream": True,
        }

        logger.info(f"调用阿里云百炼 API: model={effective_model}, base_url={effective_base_url}")

        response = await asyncio.to_thread(
            requests.post,
            url,
            headers=headers,
            json=data,
            stream=True,
            timeout=(10, 300),
        )
        if response.status_code != 200:
            body = await asyncio.to_thread(lambda: response.text or "")
            raise RuntimeError(f"LLM API {response.status_code}: {body[:200]}")

        lines = response.iter_lines()
        while True:
            line = await asyncio.to_thread(next, lines, None)
            if line is None:
                break
            if line:
                line = line.decode("utf-8")
                if line.startswith('data: '):
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

        logger.info("流式响应完成")

    except Exception as e:
        logger.error(f"阿里云百炼 API 错误: {e}")
        yield f"（AI 服务错误: {str(e)}）"


# ------------------------------------------------------------------ #
# 查询改写：检索无结果时换一种问法重试（一次非流式调用）                   #
# ------------------------------------------------------------------ #

def _api_error_detail(response) -> str:
    """提取 LLM API 错误详情（如欠费 Arrearage、限流），便于快速定位。"""
    try:
        err = response.json().get("error")
        if isinstance(err, dict):
            return err.get("message") or str(err)
        return str(err or response.text)
    except Exception:
        return response.text[:200]


def rewrite_query(question: str, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """把用户问题改写为更适合关键词/语义检索的查询；失败时原样返回。"""
    effective_key = api_key or settings.OPENAI_API_KEY
    effective_model = model or settings.DEFAULT_MODEL
    effective_base_url = base_url or settings.OPENAI_BASE_URL
    if not effective_key or not effective_base_url or not question.strip():
        return question

    try:
        resp = requests.post(
            f"{effective_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {effective_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": effective_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是检索查询改写器。把用户问题改写成更适合在知识库文档中检索的查询："
                            "提取核心概念、补充同义关键词，保持简短（不超过40字）。"
                            "只输出改写后的查询本身，不要任何解释或引号。"
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                "temperature": 0,
                "max_tokens": 80,
                "stream": False,
            },
            timeout=(10, 30),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API {resp.status_code}: {_api_error_detail(resp)}")
        rewritten = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        if rewritten and len(rewritten) <= 100:
            return rewritten
        return question
    except Exception as e:
        logger.warning("查询改写失败（使用原始查询）: %s", e)
        return question


# ------------------------------------------------------------------ #
# 生成质量自检：答案与证据的一致性（轻量，一次非流式调用）                 #
# ------------------------------------------------------------------ #

_VERIFY_PROMPT = """你是 RAG 答案质量审核器。根据「参考文档」判断「回答」质量，只输出 JSON：
{{"supported": true/false, "relevant": true/false, "reason": "一句话原因"}}

判断标准：
- supported：回答中的事实性结论是否都能从参考文档得到支持（无依据补充/事实冲突/幻觉 = false）
- relevant：回答是否真正回应了用户的问题（答非所问 = false）
- 参考文档为空或与问题无关，且回答明确说明缺少资料 → supported=true, relevant=true
只输出 JSON，不要输出其他内容。"""


def check_answer_quality(
    question: str,
    context: str,
    answer: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """返回 {"supported": bool, "relevant": bool, "reason": str}；调用失败时默认通过。"""
    effective_key = api_key or settings.OPENAI_API_KEY
    effective_model = model or settings.DEFAULT_MODEL
    effective_base_url = base_url or settings.OPENAI_BASE_URL
    if not effective_key or not effective_base_url or not answer.strip():
        return {"supported": True, "relevant": True, "reason": ""}

    prompt = (
        f"{_VERIFY_PROMPT}\n\n【用户问题】\n{question}\n\n【参考文档】\n{context[:6000]}\n\n【回答】\n{answer[:4000]}"
    )
    try:
        resp = requests.post(
            f"{effective_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {effective_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": effective_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 200,
                "stream": False,
            },
            timeout=(10, 60),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API {resp.status_code}: {_api_error_detail(resp)}")
        content = resp.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            return {"supported": True, "relevant": True, "reason": ""}
        verdict = json.loads(content[start : end + 1])
        return {
            "supported": bool(verdict.get("supported", True)),
            "relevant": bool(verdict.get("relevant", True)),
            "reason": str(verdict.get("reason", ""))[:200],
        }
    except Exception as e:
        logger.warning("答案质量自检失败（默认放行）: %s", e)
        return {"supported": True, "relevant": True, "reason": ""}
