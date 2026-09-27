import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Document, ChatSession, ChatMessage, AdminAuditLog
from auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _ok(data=None, message: str = "成功") -> dict:
    return {"code": 200, "message": message, "data": data}


def _fail(message: str, code: int = 400) -> dict:
    return {"code": code, "message": message, "data": None}


def _log_admin_action(
    db: Session,
    admin: User,
    action: str,
    target_type: str,
    target_id: str | int | None = None,
    detail: str = "",
) -> None:
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=detail,
    ))


# ------------------------------------------------------------------ #
# 系统概览                                                             #
# ------------------------------------------------------------------ #

@router.get("/stats")
def get_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    completed_documents = (
        db.query(func.count(Document.id))
        .filter(Document.status == "completed")
        .scalar() or 0
    )
    failed_documents = (
        db.query(func.count(Document.id))
        .filter(Document.status == "failed")
        .scalar() or 0
    )
    total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
    total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0

    # 存储占用
    upload_dir = "uploads"
    total_storage = 0
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            fp = os.path.join(upload_dir, f)
            if os.path.isfile(fp):
                total_storage += os.path.getsize(fp)

    return _ok({
        "total_users": total_users,
        "total_documents": total_documents,
        "completed_documents": completed_documents,
        "failed_documents": failed_documents,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_storage": total_storage,
    })


# ------------------------------------------------------------------ #
# 用户管理                                                             #
# ------------------------------------------------------------------ #

@router.get("/users")
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    search: str = Query("", description="搜索用户名或邮箱"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(User)
    if search:
        q = q.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    total = q.count()
    users = (
        q.order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    # 统计每个用户的文档数
    user_ids = [u.id for u in users]
    doc_counts = {}
    if user_ids:
        rows = (
            db.query(Document.user_id, func.count(Document.id))
            .filter(Document.user_id.in_(user_ids))
            .group_by(Document.user_id)
            .all()
        )
        doc_counts = {uid: cnt for uid, cnt in rows}

    return _ok({
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "document_count": doc_counts.get(u.id, 0),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
    })


@router.get("/documents")
def list_documents(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    search: str = Query("", description="搜索文件名或用户名"),
    status: str = Query("", description="文档状态"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Document, User).join(User, Document.user_id == User.id)
    if search:
        q = q.filter(
            (Document.original_filename.contains(search)) |
            (User.username.contains(search)) |
            (User.email.contains(search))
        )
    if status:
        q = q.filter(Document.status == status)

    total = q.count()
    rows = (
        q.order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return _ok({
        "documents": [
            {
                "id": doc.id,
                "filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size or 0,
                "status": doc.status,
                "content_type": doc.content_type,
                "word_count": doc.word_count or 0,
                "chunk_count": doc.chunk_count or 0,
                "processing_error": doc.processing_error,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                "owner": {
                    "id": owner.id,
                    "username": owner.username,
                    "email": owner.email,
                },
            }
            for doc, owner in rows
        ],
        "total": total,
    })


@router.get("/sessions")
def list_sessions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    search: str = Query("", description="搜索会话ID、用户名或邮箱"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(ChatSession, User).join(User, ChatSession.user_id == User.id)
    if search:
        q = q.filter(
            (ChatSession.id.contains(search)) |
            (User.username.contains(search)) |
            (User.email.contains(search))
        )

    total = q.count()
    rows = (
        q.order_by(ChatSession.last_activity.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    session_ids = [session.id for session, _ in rows]
    latest_messages = {}
    if session_ids:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id.in_(session_ids))
            .order_by(ChatMessage.created_at.desc())
            .all()
        )
        for message in messages:
            if message.session_id not in latest_messages:
                latest_messages[message.session_id] = message

    return _ok({
        "sessions": [
            {
                "id": session.id,
                "message_count": session.message_count or 0,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "owner": {
                    "id": owner.id,
                    "username": owner.username,
                    "email": owner.email,
                },
                "latest_message": {
                    "role": latest_messages[session.id].role,
                    "content": latest_messages[session.id].content[:120],
                    "created_at": latest_messages[session.id].created_at.isoformat()
                    if latest_messages[session.id].created_at else None,
                } if session.id in latest_messages else None,
            }
            for session, owner in rows
        ],
        "total": total,
    })


@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        return _fail("不能禁用自己", 400)
    user = db.get(User, user_id)
    if not user:
        return _fail("用户不存在", 404)
    user.is_active = not user.is_active
    _log_admin_action(
        db,
        admin,
        "toggle_user_active",
        "user",
        user.id,
        f"{admin.username} 将用户 {user.username} 状态改为 {'启用' if user.is_active else '禁用'}",
    )
    db.commit()
    return _ok({
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
    }, f"用户已{'启用' if user.is_active else '禁用'}")


@router.put("/users/{user_id}/toggle-admin")
def toggle_user_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        return _fail("不能修改自己的管理员权限", 400)
    user = db.get(User, user_id)
    if not user:
        return _fail("用户不存在", 404)
    user.is_superuser = not user.is_superuser
    _log_admin_action(
        db,
        admin,
        "toggle_user_admin",
        "user",
        user.id,
        f"{admin.username} {'授予' if user.is_superuser else '撤销'}用户 {user.username} 的管理员权限",
    )
    db.commit()
    return _ok({
        "id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser,
    }, f"管理员权限已{'授予' if user.is_superuser else '撤销'}")


@router.get("/audit-logs")
def list_audit_logs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(AdminAuditLog, User).join(User, AdminAuditLog.admin_id == User.id)
    total = q.count()
    rows = (
        q.order_by(AdminAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return _ok({
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "admin": {
                    "id": actor.id,
                    "username": actor.username,
                    "email": actor.email,
                },
            }
            for log, actor in rows
        ],
        "total": total,
    })
