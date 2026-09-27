import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import User, Document, DocumentCategory
from auth import get_current_user
from config import settings
from services.document_processor import chunk_document, count_words, extract_structured
from services import retrieval
from schemas import DocumentCategoryCreate, DocumentCategoryUpdate

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS | settings.IMAGE_EXTENSIONS
UPLOAD_CHUNK_SIZE = 1024 * 1024


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _ok(data=None, message: str = "成功") -> dict:
    return {"code": 200, "message": message, "data": data}


def _fail(message: str, code: int = 400) -> dict:
    return {"code": code, "message": message, "data": None}


def _fail_response(http_status: int, message: str, code: int | None = None) -> JSONResponse:
    body = _fail(message, code if code is not None else http_status)
    return JSONResponse(status_code=http_status, content=body)


def _doc_dict(doc: Document) -> dict:
    progress_map = {
        "uploading": "文件正在上传",
        "processing": "正在解析文本、切分内容并写入向量库",
        "completed": "处理完成，可用于 AI 问答",
        "failed": "处理失败，请查看失败原因后重试",
    }
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "content_type": doc.content_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "category_id": doc.category_id,
        "category_name": doc.category.name if getattr(doc, "category", None) else None,
        "word_count": doc.word_count,
        "chunk_count": doc.chunk_count,
        "processing_error": doc.processing_error,
        "progress_text": progress_map.get(doc.status, "状态未知"),
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
    }


# ------------------------------------------------------------------ #
# Background processing                                                #
# ------------------------------------------------------------------ #

def _process_document(
    doc_id: int,
    file_path: str,
    file_type: str,
    user_id: int,
    filename: str,
) -> None:
    """Runs in a thread-pool thread — creates its own DB session."""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            return

        try:
            doc.status = "processing"
            db.commit()

            # 按页面类型路由解析（PDF 扫描页 OCR、表格转 Markdown 等），输出结构块
            blocks = extract_structured(file_path, file_type)
            if not blocks:
                raise ValueError("无法从文件中提取文本内容")

            # 结构感知分块，chunk 携带页码/小节元数据
            chunks = chunk_document(blocks)
            if not chunks:
                raise ValueError("文档分块结果为空")
            wc = count_words("\n".join(b["text"] for b in blocks))

            last_error = None
            for _ in range(2):
                try:
                    retrieval.add_document(user_id, doc_id, chunks, filename)
                    last_error = None
                    break
                except Exception as err:
                    last_error = err
            if last_error is not None:
                raise RuntimeError(f"VECTOR_STORE_ERROR: {last_error}")

            doc.status = "completed"
            doc.word_count = wc
            doc.chunk_count = len(chunks)
            doc.processed_at = datetime.now(timezone.utc)
        except Exception as exc:
            doc.status = "failed"
            doc.processing_error = str(exc)

        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------------ #
# Endpoints                                                            #
# ------------------------------------------------------------------ #

@router.get("/categories")
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = (
        db.query(DocumentCategory)
        .filter(DocumentCategory.user_id == current_user.id)
        .order_by(DocumentCategory.created_at.desc())
        .all()
    )
    if not categories:
        return _ok({"categories": []})

    counts = dict(
        db.query(Document.category_id, func.count(Document.id))
        .filter(Document.user_id == current_user.id, Document.category_id.isnot(None))
        .group_by(Document.category_id)
        .all()
    )
    data = [
        {
            "id": c.id,
            "name": c.name,
            "document_count": int(counts.get(c.id, 0)),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in categories
    ]
    return _ok({"categories": data})


@router.post("/categories")
def create_category(
    body: DocumentCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (body.name or "").strip()
    if not name:
        return _fail("分类名称不能为空")

    exists = (
        db.query(DocumentCategory)
        .filter(DocumentCategory.user_id == current_user.id, DocumentCategory.name == name)
        .first()
    )
    if exists:
        return _fail("分类名称已存在")

    category = DocumentCategory(user_id=current_user.id, name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return _ok({
        "id": category.id,
        "name": category.name,
        "document_count": 0,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }, "创建分类成功")


@router.patch("/categories/{category_id}")
def rename_category(
    category_id: int,
    body: DocumentCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = (
        db.query(DocumentCategory)
        .filter(DocumentCategory.id == category_id, DocumentCategory.user_id == current_user.id)
        .first()
    )
    if not category:
        return _fail("分类不存在", 404)

    name = (body.name or "").strip()
    if not name:
        return _fail("分类名称不能为空")

    exists = (
        db.query(DocumentCategory)
        .filter(
            DocumentCategory.user_id == current_user.id,
            DocumentCategory.name == name,
            DocumentCategory.id != category_id,
        )
        .first()
    )
    if exists:
        return _fail("分类名称已存在")

    category.name = name
    db.commit()
    db.refresh(category)
    return _ok({
        "id": category.id,
        "name": category.name,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }, "重命名成功")


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = (
        db.query(DocumentCategory)
        .filter(DocumentCategory.id == category_id, DocumentCategory.user_id == current_user.id)
        .first()
    )
    if not category:
        return _fail("分类不存在", 404)

    db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.category_id == category_id,
    ).update({Document.category_id: None}, synchronize_session=False)

    db.delete(category)
    db.commit()
    return _ok(None, "分类已删除")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category_id: int | None = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _fail_response(
            status.HTTP_400_BAD_REQUEST,
            f"不支持该文件格式（{ext}），仅支持 PDF/DOCX/TXT/MD/PNG/JPG/JPEG/WEBP/BMP",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _fail_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "创建上传目录失败")

    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / stored_name

    content_type = "image" if ext in settings.IMAGE_EXTENSIONS else "text"
    size_limit = settings.MAX_IMAGE_SIZE if content_type == "image" else settings.MAX_FILE_SIZE

    total_size = 0
    hasher = hashlib.sha256()
    try:
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > size_limit:
                    raise ValueError("file_too_large")
                hasher.update(chunk)
                f.write(chunk)
    except ValueError as exc:
        if str(exc) == "file_too_large":
            if file_path.exists():
                file_path.unlink()
            return _fail_response(status.HTTP_413_CONTENT_TOO_LARGE, "文件超过大小限制")
        if file_path.exists():
            file_path.unlink()
        return _fail_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "上传失败")
    except OSError:
        if file_path.exists():
            file_path.unlink()
        return _fail_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "保存文件失败")

    fallback_mime = f"image/{'jpeg' if ext == '.jpg' else ext.lstrip('.')}" if content_type == "image" else f"application/{ext.lstrip('.')}"

    file_hash = hasher.hexdigest()

    # 文件哈希去重：同一用户重复上传同一文件时直接拦截（体检阶段）
    duplicate = (
        db.query(Document)
        .filter(
            Document.user_id == current_user.id,
            Document.file_hash == file_hash,
            Document.status.in_(["processing", "completed"]),
        )
        .first()
    )
    if duplicate:
        file_path.unlink(missing_ok=True)
        return _fail_response(
            status.HTTP_409_CONFLICT,
            f"重复文件：与已上传的《{duplicate.original_filename}》内容相同",
        )

    if category_id is not None:
        category = (
            db.query(DocumentCategory)
            .filter(DocumentCategory.id == category_id, DocumentCategory.user_id == current_user.id)
            .first()
        )
        if not category:
            if file_path.exists():
                file_path.unlink()
            return _fail_response(status.HTTP_400_BAD_REQUEST, "分类不存在或无权限")

    doc = Document(
        user_id=current_user.id,
        category_id=category_id,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_type=file.content_type or fallback_mime,
        content_type=content_type,
        file_size=total_size,
        file_hash=file_hash,
        status="processing",
    )
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        return _fail_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "保存文档记录失败")

    background_tasks.add_task(
        _process_document,
        doc.id,
        str(file_path),
        doc.file_type,
        current_user.id,
        file.filename,
    )

    return _ok(_doc_dict(doc), "上传成功，正在后台处理")


@router.get("")
def list_documents(
    skip: int = 0,
    limit: int = 10,
    category_id: int | None = None,
    uncategorized: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Document).filter(Document.user_id == current_user.id)
    if uncategorized:
        q = q.filter(Document.category_id.is_(None))
    elif category_id is not None:
        q = q.filter(Document.category_id == category_id)
    total = q.count()
    docs = q.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    return _ok({"documents": [_doc_dict(d) for d in docs], "total": total})


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        return _fail("文档不存在", 404)
    return _ok(_doc_dict(doc))


@router.get("/{doc_id}/status")
def get_document_status(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        return _fail("文档不存在", 404)
    return _ok({"status": doc.status, "processing_error": doc.processing_error})


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        return _fail("文档不存在", 404)

    retrieval.delete_document(current_user.id, doc_id)

    file_path = Path(settings.UPLOAD_DIR) / doc.stored_filename
    if file_path.exists():
        file_path.unlink()

    db.delete(doc)
    db.commit()
    return _ok(None, "删除成功")


@router.post("/{doc_id}/process")
async def reprocess_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        return _fail("文档不存在", 404)

    file_path = Path(settings.UPLOAD_DIR) / doc.stored_filename
    if not file_path.exists():
        return _fail("原始文件不存在，无法重新处理")

    retrieval.delete_document(current_user.id, doc_id)
    doc.status = "processing"
    doc.processing_error = None
    db.commit()

    background_tasks.add_task(
        _process_document,
        doc.id,
        str(file_path),
        doc.file_type,
        current_user.id,
        doc.original_filename,
    )
    return _ok(_doc_dict(doc), "已开始重新处理")
