import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import User, ChatSession, ChatMessage, UserAIConfig, Document, DocumentCategory
from auth import get_current_user, get_optional_user
from config import settings
from schemas import ChatRequest, ClearHistoryRequest
from services import retrieval
from services.ai_service import stream_response, check_answer_quality, _build_context

router = APIRouter(prefix="/chat", tags=["chat"])


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _ok(data=None, message: str = "成功") -> dict:
    return {"code": 200, "message": message, "data": data}


def _fail(message: str, code: int = 400) -> dict:
    return {"code": code, "message": message, "data": None}


def _iso_utc_z(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _msg_dict(msg: ChatMessage) -> dict:
    sources: list = []
    if msg.sources:
        try:
            sources = json.loads(msg.sources)
        except Exception:
            pass
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "session_id": msg.session_id,
        "sources": sources,
        "response_time": msg.response_time,
        "created_at": _iso_utc_z(msg.created_at),
    }


def _source_dict(chunk: dict) -> dict:
    content = (chunk.get("content") or "").strip()
    return {
        "filename": chunk.get("filename"),
        "document_id": chunk.get("document_id"),
        "chunk_index": chunk.get("chunk_index"),
        "similarity": chunk.get("similarity"),
        "page_number": chunk.get("page_number"),
        "section": chunk.get("section"),
        "kind": chunk.get("kind"),
        "snippet": content[:260],
    }


def _get_or_create_session(db: Session, session_id: str, user_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if not session:
        session = ChatSession(id=session_id, user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def _validate_selected_documents(db: Session, user_id: int, document_ids: list[int]) -> list[int]:
    docs = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.id.in_(document_ids),
            Document.status == "completed",
            Document.content_type.in_(["text", "image"]),
        )
        .all()
    )
    valid_ids = {d.id for d in docs}
    if len(valid_ids) != len(set(document_ids)):
        raise ValueError("所选文档不存在、未完成处理或不属于当前用户")
    return document_ids


def _ensure_category_access(db: Session, user_id: int, category_id: int) -> None:
    if category_id == 0:
        return
    category = (
        db.query(DocumentCategory)
        .filter(DocumentCategory.id == category_id, DocumentCategory.user_id == user_id)
        .first()
    )
    if not category:
        raise ValueError("所选分类不存在或不属于当前用户")


def _resolve_documents_by_category(db: Session, user_id: int, category_id: int) -> list[int]:
    q = db.query(Document.id).filter(
        Document.user_id == user_id,
        Document.status == "completed",
        Document.content_type.in_(["text", "image"]),
    )
    if category_id == 0:
        q = q.filter(Document.category_id.is_(None))
    else:
        q = q.filter(Document.category_id == category_id)
    return [row[0] for row in q.all()]


def _ensure_docs_in_category(db: Session, user_id: int, category_id: int, document_ids: list[int]) -> None:
    q = db.query(Document.id).filter(
        Document.user_id == user_id,
        Document.id.in_(document_ids),
    )
    if category_id == 0:
        q = q.filter(Document.category_id.is_(None))
    else:
        q = q.filter(Document.category_id == category_id)
    matched = {row[0] for row in q.all()}
    if len(matched) != len(set(document_ids)):
        raise ValueError("所选文档不属于当前分类")


# ------------------------------------------------------------------ #
# Streaming chat                                                       #
# ------------------------------------------------------------------ #

@router.post("/ask")
async def ask(
    body: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    message = body.message.strip()
    if not message:
        return _fail("消息不能为空")

    mode = body.chat_mode or "free"
    if mode not in ("free", "rag_selected"):
        return _fail("不支持的对话模式")

    user_id: Optional[int] = current_user.id if current_user else None
    session_id = body.session_id or str(uuid.uuid4())

    # Persist user message and create/load session (authenticated only)
    history: list[dict] = []
    if current_user:
        session = _get_or_create_session(db, session_id, user_id)

        # Load recent history for context
        prior = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in prior]

        # Save user message
        db.add(
            ChatMessage(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=message,
            )
        )
        db.commit()

    # Load user's custom AI config if authenticated
    ai_cfg = None
    if current_user:
        ai_cfg = db.query(UserAIConfig).filter(UserAIConfig.user_id == current_user.id).first()

    # Retrieve relevant context from vector store
    retrieved: list[dict] = []
    if mode == "rag_selected":
        if not user_id:
            return _fail("请先登录后使用文档问答模式", 401)

        selected_ids = body.selected_document_ids or []
        selected_category_id = body.selected_category_id

        try:
            if selected_ids:
                valid_ids = _validate_selected_documents(db, user_id, selected_ids)
                if selected_category_id is not None:
                    _ensure_category_access(db, user_id, selected_category_id)
                    _ensure_docs_in_category(db, user_id, selected_category_id, valid_ids)
            elif selected_category_id is not None:
                _ensure_category_access(db, user_id, selected_category_id)
                valid_ids = _resolve_documents_by_category(db, user_id, selected_category_id)
                if not valid_ids:
                    return _fail("当前分类下没有可用文档，请先上传并处理完成")
            else:
                return _fail("请先选择分类或文档后再提问")
        except ValueError as exc:
            return _fail(str(exc))

        retrieved = retrieval.search(user_id, message, document_ids=valid_ids)

    start_ts = time.time()

    async def _generate():
        full_text = ""
        sources = [_source_dict(c) for c in retrieved]

        # 检索去噪后无可用证据：直接拒答，不进入生成环节
        if mode == "rag_selected" and not retrieved:
            refuse = (
                "当前文档中未检索到与问题相关的内容。"
                "请确认已上传相关文档、文档处理完成，或换一种问法再试。"
            )
            yield (
                f"data: {json.dumps({'type': 'context', 'metadata': {'session_id': session_id, 'sources': []}}, ensure_ascii=False)}\n\n"
            )
            yield f"data: {json.dumps({'type': 'token', 'content': refuse}, ensure_ascii=False)}\n\n"
            yield (
                f"data: {json.dumps({'type': 'complete', 'metadata': {'session_id': session_id, 'sources': [], 'quality': {'supported': True, 'relevant': True, 'reason': 'no_evidence_refusal'}}}, ensure_ascii=False)}\n\n"
            )
            if current_user:
                _db = SessionLocal()
                try:
                    _db.add(
                        ChatMessage(
                            session_id=session_id,
                            user_id=current_user.id,
                            role="assistant",
                            content=refuse,
                            sources="[]",
                            response_time=int((time.time() - start_ts) * 1000),
                        )
                    )
                    sess = _db.get(ChatSession, session_id)
                    if sess:
                        sess.last_activity = datetime.now(timezone.utc)
                        sess.message_count = (
                            _db.query(ChatMessage)
                            .filter(ChatMessage.session_id == session_id)
                            .count()
                        )
                    _db.commit()
                finally:
                    _db.close()
            return

        yield (
            f"data: {json.dumps({'type': 'context', 'metadata': {'session_id': session_id, 'sources': sources}}, ensure_ascii=False)}\n\n"
        )

        try:
            async for token in stream_response(
                message, retrieved, history,
                chat_mode=mode,
                model=ai_cfg.model if ai_cfg else None,
                base_url=ai_cfg.base_url if ai_cfg else None,
                api_key=ai_cfg.api_key if ai_cfg else None,
            ):
                full_text += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
            return

        # 生成质量闭环：答案-证据一致性自检，不通过则补一次严格依据证据的修正
        quality = {"supported": True, "relevant": True, "reason": ""}
        if settings.RAG_VERIFY_ENABLED and mode == "rag_selected":
            effective_key = (ai_cfg.api_key if ai_cfg else None) or settings.OPENAI_API_KEY
            effective_model = (ai_cfg.model if ai_cfg else None) or settings.DEFAULT_MODEL
            effective_base_url = (ai_cfg.base_url if ai_cfg else None) or settings.OPENAI_BASE_URL
            quality = await asyncio.to_thread(
                check_answer_quality,
                message,
                _build_context(retrieved),
                full_text,
                effective_model,
                effective_base_url,
                effective_key,
            )
            yield (
                f"data: {json.dumps({'type': 'quality', 'content': quality}, ensure_ascii=False)}\n\n"
            )
            if not (quality["supported"] and quality["relevant"]):
                yield (
                    f"data: {json.dumps({'type': 'token', 'content': '\n\n---\n**修正（严格依据参考文档）：**\n\n'}, ensure_ascii=False)}\n\n"
                )
                try:
                    async for token in stream_response(
                        message, retrieved, history,
                        chat_mode=mode,
                        model=ai_cfg.model if ai_cfg else None,
                        base_url=ai_cfg.base_url if ai_cfg else None,
                        api_key=ai_cfg.api_key if ai_cfg else None,
                        retry_strict=True,
                    ):
                        full_text += token
                        yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
                except Exception as exc:
                    logger_warning = f"修正生成失败: {exc}"
                    yield f"data: {json.dumps({'type': 'token', 'content': f'\n（{logger_warning}）'}, ensure_ascii=False)}\n\n"

        response_ms = int((time.time() - start_ts) * 1000)

        # Persist assistant message in a fresh session
        if current_user and full_text:
            _db = SessionLocal()
            try:
                _db.add(
                    ChatMessage(
                        session_id=session_id,
                        user_id=current_user.id,
                        role="assistant",
                        content=full_text,
                        sources=json.dumps(sources, ensure_ascii=False),
                        response_time=response_ms,
                    )
                )
                sess = _db.get(ChatSession, session_id)
                if sess:
                    sess.last_activity = datetime.now(timezone.utc)
                    sess.message_count = (
                        _db.query(ChatMessage)
                        .filter(ChatMessage.session_id == session_id)
                        .count()
                    )
                _db.commit()
            finally:
                _db.close()

        yield (
            f"data: {json.dumps({'type': 'complete', 'metadata': {'session_id': session_id, 'sources': sources, 'quality': quality}}, ensure_ascii=False)}\n\n"
        )

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------------ #
# Sync chat (non-streaming fallback)                                   #
# ------------------------------------------------------------------ #

@router.post("/ask/sync")
async def ask_sync(
    body: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    message = body.message.strip()
    if not message:
        return _fail("消息不能为空")

    mode = body.chat_mode or "free"
    if mode not in ("free", "rag_selected"):
        return _fail("不支持的对话模式")

    user_id = current_user.id if current_user else None
    session_id = body.session_id or str(uuid.uuid4())

    history: list[dict] = []
    if current_user:
        _get_or_create_session(db, session_id, user_id)
        prior = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in prior]
        db.add(ChatMessage(session_id=session_id, user_id=user_id, role="user", content=message))
        db.commit()

    ai_cfg_sync = None
    if current_user:
        ai_cfg_sync = db.query(UserAIConfig).filter(UserAIConfig.user_id == current_user.id).first()

    retrieved = []
    if mode == "rag_selected":
        if not user_id:
            return _fail("请先登录后使用文档问答模式", 401)

        selected_ids = body.selected_document_ids or []
        selected_category_id = body.selected_category_id

        try:
            if selected_ids:
                valid_ids = _validate_selected_documents(db, user_id, selected_ids)
                if selected_category_id is not None:
                    _ensure_category_access(db, user_id, selected_category_id)
                    _ensure_docs_in_category(db, user_id, selected_category_id, valid_ids)
            elif selected_category_id is not None:
                _ensure_category_access(db, user_id, selected_category_id)
                valid_ids = _resolve_documents_by_category(db, user_id, selected_category_id)
                if not valid_ids:
                    return _fail("当前分类下没有可用文档，请先上传并处理完成")
            else:
                return _fail("请先选择分类或文档后再提问")
        except ValueError as exc:
            return _fail(str(exc))

        retrieved = retrieval.search(user_id, message, document_ids=valid_ids)

    start_ts = time.time()

    full_text = ""
    async for token in stream_response(
        message, retrieved, history,
        chat_mode=mode,
        model=ai_cfg_sync.model if ai_cfg_sync else None,
        base_url=ai_cfg_sync.base_url if ai_cfg_sync else None,
        api_key=ai_cfg_sync.api_key if ai_cfg_sync else None,
    ):
        full_text += token

    response_ms = int((time.time() - start_ts) * 1000)
    sources = [_source_dict(c) for c in retrieved]

    if current_user and full_text:
        db.add(
            ChatMessage(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_text,
                sources=json.dumps(sources, ensure_ascii=False),
                response_time=response_ms,
            )
        )
        sess = db.get(ChatSession, session_id)
        if sess:
            sess.last_activity = datetime.now(timezone.utc)
            sess.message_count += 2
        db.commit()

    return _ok(
        {
            "content": full_text,
            "session_id": session_id,
            "sources": sources,
            "response_time": response_ms,
        }
    )


# ------------------------------------------------------------------ #
# History & sessions                                                   #
# ------------------------------------------------------------------ #

@router.get("/sessions")
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.last_activity.desc())
        .all()
    )
    data = []
    for s in sessions:
        first_user_message = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == s.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        data.append(
            {
                "session_id": s.id,
                "last_activity": _iso_utc_z(s.last_activity),
                "message_count": s.message_count,
                "created_at": _iso_utc_z(s.created_at),
                "first_question": first_user_message.content if first_user_message else "",
            }
        )
    return _ok({"sessions": data})


@router.get("/history")
def get_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if session_id:
        q = q.filter(ChatMessage.session_id == session_id)
    total = q.count()
    msgs = q.order_by(ChatMessage.created_at).offset(offset).limit(limit).all()
    return _ok({"messages": [_msg_dict(m) for m in msgs], "total": total})


@router.delete("/clear")
def clear_history(
    body: ClearHistoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.session_id:
        session = db.get(ChatSession, body.session_id)
        if session and session.user_id == current_user.id:
            db.delete(session)
            db.commit()
    else:
        sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
        for s in sessions:
            db.delete(s)
        db.commit()
    return _ok(None, "对话记录已清空")
