"""文档解析与结构感知分块。

解析遵循「文件基础体检 → 逐页判断类型 → 按页面类型解析 → 统一结果」的流程：

- PDF：优先用 PyMuPDF 逐页提取，按文字量 / 图片覆盖率把页面分为原生文本页、
  扫描页、混合页、异常页；扫描页与混合页的图片区域走 OCR 兜底；
  尝试用 find_tables 恢复表格为 Markdown。
- DOCX：按正文顺序遍历段落与表格，标题样式识别为小节名，表格转 Markdown。
- Markdown / 纯文本：按标题行切出结构块。

统一输出「块」列表：{"text", "page_number", "section", "kind"}，
再由 chunk_document 做结构感知分块，chunk 携带 page_number / section 元数据，
保证结果可追溯到原文。
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)

Block = Dict[str, Any]  # {"text", "page_number", "section", "kind"}

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_PRIVATE_USE_RE = re.compile(r"[\uE000-\uF8FF]")


# ------------------------------------------------------------------ #
# 文件级体检                                                          #
# ------------------------------------------------------------------ #

def compute_file_hash(file_path: str) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ #
# 解析入口                                                            #
# ------------------------------------------------------------------ #

def extract_structured(file_path: str, file_type: str) -> List[Block]:
    """按文件类型分发，返回统一结构块列表。"""
    fp = Path(file_path)
    ext = fp.suffix.lower()
    mime = (file_type or "").lower()

    if ext in settings.IMAGE_EXTENSIONS or mime.startswith("image/"):
        return _blocks_from_image(file_path, file_type)
    if "pdf" in mime or ext == ".pdf":
        return _extract_pdf_blocks(file_path)
    if "word" in mime or "docx" in mime or ext == ".docx":
        return _extract_docx_blocks(file_path)
    if ext == ".md" or ext == ".markdown":
        return _extract_markdown_blocks(file_path)
    return _extract_plain_blocks(file_path)


def extract_text(file_path: str, file_type: str) -> str:
    """兼容旧接口：提取全文纯文本。"""
    blocks = extract_structured(file_path, file_type)
    return "\n".join(b["text"] for b in blocks)


# ------------------------------------------------------------------ #
# PDF：逐页分类路由                                                    #
# ------------------------------------------------------------------ #

def _abnormal_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    abnormal = len(_PRIVATE_USE_RE.findall(text)) + text.count("\ufffd")
    return abnormal / max(1, len(text))


def _extract_pdf_blocks(file_path: str) -> List[Block]:
    try:
        try:
            import pymupdf as fitz  # PyMuPDF
        except ImportError:
            import fitz  # 旧版 PyMuPDF
    except ImportError:
        logger.warning("未安装 PyMuPDF，PDF 回退到 pdfplumber 整篇提取（无页码/分类）")
        return _extract_pdf_blocks_fallback(file_path)

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"PDF 损坏或无法打开: {e}")

    try:
        if doc.needs_pass:
            # 体检：加密文档先尝试空密码，失败则明确报错
            if not doc.authenticate(""):
                raise ValueError("PDF 已加密，请先解密后重新上传")

        blocks: List[Block] = []
        ocr_budget = settings.RAG_OCR_MAX_PAGES
        current_section: Optional[str] = None

        for page_no, page in enumerate(doc, start=1):
            page_area = float(abs(page.rect)) or 1.0
            text = (page.get_text("text") or "").strip()
            clean_chars = len(re.sub(r"\s", "", text))
            abnormal_ratio = _abnormal_char_ratio(text)

            # 图片覆盖率
            image_area = 0.0
            for xref in page.get_images(full=True):
                try:
                    for rect in page.get_image_rects(xref[0]):
                        image_area += float(abs(rect))
                except Exception:
                    continue
            image_ratio = min(1.0, image_area / page_area)

            if abnormal_ratio > 0.3 and clean_chars > 0:
                page_type = "abnormal"
            elif clean_chars < settings.RAG_SCANNED_PAGE_MIN_CHARS and image_ratio >= 0.5:
                page_type = "scanned"
            elif clean_chars >= settings.RAG_SCANNED_PAGE_MIN_CHARS and image_ratio >= settings.RAG_IMAGE_MIN_AREA_RATIO:
                page_type = "mixed"
            elif clean_chars < settings.RAG_SCANNED_PAGE_MIN_CHARS:
                page_type = "abnormal"
            else:
                page_type = "native"

            page_blocks, current_section = _parse_pdf_page(
                doc, page, page_no, page_type, ocr_budget, current_section
            )
            ocr_budget -= sum(1 for b in page_blocks if b["kind"] == "ocr")
            blocks.extend(page_blocks)

        return blocks
    finally:
        doc.close()


def _parse_pdf_page(doc, page, page_no: int, page_type: str, ocr_budget: int, inherited_section: Optional[str] = None):
    from services.image_ocr_service import extract_image_text_from_bytes

    blocks: List[Block] = []
    current_section = inherited_section

    # 1) 表格优先：find_tables 恢复为 Markdown，避免被当正文打乱
    table_regions = []
    try:
        for table in page.find_tables():
            data = table.extract()
            if not data:
                continue
            md = _table_to_markdown(data)
            if md:
                blocks.append({"text": md, "page_number": page_no, "section": None, "kind": "table"})
                table_regions.append(table.bbox)
    except Exception as e:
        logger.debug("第 %s 页表格识别失败: %s", page_no, e)

    # 2) 正文：按文本块读取顺序提取（双栏排序启发式），标题行处切段并归属小节
    headings = _detect_headings(page) if page_type in ("native", "mixed") else set()
    segments, page_last_heading = _page_reading_order_text(page, table_regions, headings)
    if page_last_heading:
        current_section = page_last_heading

    def _tag(block: Block) -> Block:
        block["section"] = block.get("section") or current_section
        return block

    if page_type in ("native", "mixed"):
        text_blocks: List[Block] = []
        for seg in segments:
            if seg["text"].strip():
                text_blocks.append(
                    _tag({"text": seg["text"].strip(), "page_number": page_no,
                          "section": seg["section"], "kind": "text"})
                )
        blocks = text_blocks + blocks  # 正文在前，表格块在后
    elif page_type == "abnormal":
        joined = "\n".join(s["text"] for s in segments).strip()
        if joined and _abnormal_char_ratio(joined) < 0.3:
            blocks.insert(0, _tag({"text": joined, "page_number": page_no, "section": None, "kind": "text"}))

    # 3) 图片路由
    if page_type == "scanned":
        if ocr_budget > 0:
            ocr_text = _ocr_page_render(doc, page)
            if ocr_text:
                blocks.append(_tag({"text": ocr_text, "page_number": page_no, "section": None, "kind": "ocr"}))
        else:
            logger.warning("第 %s 页需要 OCR 但超出单文档 OCR 配额，已跳过", page_no)
    elif page_type == "mixed":
        if ocr_budget > 0:
            for img_bytes in _significant_page_images(page):
                if ocr_budget <= 0:
                    break
                try:
                    ocr_text = extract_image_text_from_bytes(img_bytes)
                    if ocr_text:
                        blocks.append(_tag({"text": ocr_text, "page_number": page_no, "section": None, "kind": "ocr"}))
                        ocr_budget -= 1
                except Exception as e:
                    logger.debug("第 %s 页内嵌图片 OCR 失败: %s", page_no, e)
        # 乱码异常页兜底：文字无法恢复时渲染整页 OCR
    elif page_type == "abnormal" and not blocks and ocr_budget > 0:
        ocr_text = _ocr_page_render(doc, page)
        if ocr_text:
            blocks.append(_tag({"text": ocr_text, "page_number": page_no, "section": None, "kind": "ocr"}))

    # 表格块归属当前小节
    for b in blocks:
        if b["kind"] == "table":
            b["section"] = b.get("section") or current_section

    return blocks, current_section


def _detect_headings(page) -> set:
    """用字号启发式识别页面小节标题：显著大于正文字号、短行、非标点结尾。"""
    try:
        data = page.get_text("dict") or {}
    except Exception:
        return set()

    lines = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            size = max((span.get("size", 0.0) for span in line.get("spans", [])), default=0.0)
            lines.append((text, size))
    if len(lines) < 3:
        return set()

    sizes = sorted(s for _, s in lines)
    # 取最小字号作为正文基准：页面标题行较多时中位数会被抬高导致漏检
    body_size = sizes[0]

    headings = set()
    for text, size in lines:
        if size < body_size + 1.5:
            continue
        if len(text) > 60:
            continue
        if text.endswith(("。", "，", "；", "：", ",", ".", ";", ":", "、")):
            continue
        if re.fullmatch(r"[-—\s\d.]+", text):  # 页码/分隔线
            continue
        headings.add(text)
    return headings


def _page_reading_order_text(page, exclude_rects: list, headings: set | None = None):
    """按块坐标恢复阅读顺序，识别双栏时先读完左栏再读右栏。

    返回 (segments, last_heading)：segments 为 [{"section", "text"}]，
    检测到标题行时在标题处切段，保证每段归属正确的小节。
    """
    headings = headings or set()
    try:
        raw = page.get_text("blocks") or []
    except Exception:
        return [{"section": None, "text": page.get_text("text") or ""}], None

    rects = []
    for b in raw:
        if len(b) < 5 or not str(b[4] or "").strip():
            continue
        r = fitz_rect(b)
        if any(_rect_overlap_ratio(r, ex) > 0.5 for ex in exclude_rects):
            continue
        rects.append((b, r))
    if not rects:
        return ""

    # 双栏检测：块中心 x 明显分成两簇（页面中线两侧且几乎无跨越中线的块）
    page_width = page.rect.width
    mid = page_width / 2
    centers = sorted(((b[0] + b[2]) / 2 for b, _ in rects))
    crossing = sum(1 for b, r in rects if r.x0 < mid - 20 and r.x1 > mid + 20)
    two_column = (
        crossing == 0
        and len(rects) >= 4
        and centers[len(centers) // 2] - centers[max(0, len(centers) // 2 - 1)] > page_width * 0.15
    )

    if two_column:
        left = [(b, r) for b, r in rects if (b[0] + b[2]) / 2 <= mid]
        right = [(b, r) for b, r in rects if (b[0] + b[2]) / 2 > mid]
        ordered = sorted(left, key=lambda x: (round(x[0][1]), x[0][0])) + sorted(
            right, key=lambda x: (round(x[0][1]), x[0][0])
        )
    else:
        ordered = sorted(rects, key=lambda x: (round(x[0][1] / 10), x[0][0]))

    ordered_texts = [str(b[4]).strip() for b, _ in ordered]

    # 在标题行处切段，段内归属同一个小节
    segments: List[Dict[str, Any]] = []
    cur_sec: Optional[str] = None
    cur_lines: List[str] = []
    for block_text in ordered_texts:
        for line in block_text.splitlines():
            line_s = line.strip()
            if line_s and line_s in headings:
                if cur_lines:
                    segments.append({"section": cur_sec, "text": "\n".join(cur_lines)})
                cur_lines = []
                cur_sec = line_s
            cur_lines.append(line)
    if cur_lines:
        segments.append({"section": cur_sec, "text": "\n".join(cur_lines)})

    last_heading = next((s["section"] for s in reversed(segments) if s["section"]), None)
    return segments, last_heading


def fitz_rect(block):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz.Rect(block[0], block[1], block[2], block[3])


def _rect_overlap_ratio(a, b) -> float:
    inter = a & b
    if inter.is_empty or a.is_empty:
        return 0.0
    return float(abs(inter)) / max(1e-6, float(abs(a)))


def _ocr_page_render(doc, page) -> str:
    from services.image_ocr_service import extract_image_text_from_bytes

    try:
        pix = page.get_pixmap(matrix=fitz_matrix(2.0))
        return (extract_image_text_from_bytes(pix.tobytes("png")) or "").strip()
    except Exception as e:
        logger.debug("整页 OCR 失败: %s", e)
        return ""


def fitz_matrix(zoom: float):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz.Matrix(zoom, zoom)


def _significant_page_images(page) -> list:
    page_area = float(abs(page.rect)) or 1.0
    images = []
    for xref in page.get_images(full=True):
        try:
            rects = page.get_image_rects(xref[0])
            area = sum(float(abs(r)) for r in rects)
            if area / page_area < settings.RAG_IMAGE_MIN_AREA_RATIO:
                continue
            images.append((area, xref[0]))
        except Exception:
            continue
    images.sort(reverse=True)
    out = []
    for _, xref in images:
        try:
            raw = page.parent.extract_image(xref)
            if raw and raw.get("image"):
                out.append(raw["image"])
        except Exception:
            continue
    return out


def _extract_pdf_blocks_fallback(file_path: str) -> List[Block]:
    try:
        import pdfplumber

        blocks: List[Block] = []
        with pdfplumber.open(file_path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    blocks.append({"text": text.strip(), "page_number": page_no, "section": None, "kind": "text"})
        return blocks
    except ImportError as e:
        raise ImportError(f"缺少 PDF 解析库，请安装 pymupdf / pdfplumber. 错误: {e}")
    except Exception as e:
        raise ValueError(f"读取 PDF 文档失败: {e}")


def _table_to_markdown(data: List[List[Optional[str]]]) -> str:
    rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in data]
    rows = [r for r in rows if any(r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ #
# DOCX / Markdown / 纯文本 / 图片                                     #
# ------------------------------------------------------------------ #

def _extract_docx_blocks(file_path: str) -> List[Block]:
    try:
        from docx import Document
        from docx.document import Document as _DocumentBody
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as e:
        raise ImportError(f"缺少 python-docx 库，请运行 pip install python-docx. 错误: {e}")

    try:
        doc = Document(file_path)
    except Exception as e:
        raise ValueError(f"Word 文档损坏或无法打开: {e}")

    def iter_blocks(parent):
        for child in parent.element.body.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    blocks: List[Block] = []
    current_section: Optional[str] = None
    for item in iter_blocks(doc):
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
            style = (item.style.name or "").lower() if item.style is not None else ""
            if ("heading" in style or "标题" in style) and len(text) < 80:
                current_section = text
                blocks.append({"text": text, "page_number": None, "section": text, "kind": "heading"})
            else:
                blocks.append({"text": text, "page_number": None, "section": current_section, "kind": "text"})
        else:  # Table
            rows = []
            for row in item.rows:
                rows.append([(cell.text or "").replace("\n", " ").strip() for cell in row.cells])
            md = _table_to_markdown(rows)
            if md:
                blocks.append(
                    {"text": md, "page_number": None, "section": current_section, "kind": "table"}
                )
    return blocks


def _extract_markdown_blocks(file_path: str) -> List[Block]:
    raw = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    lines = raw.splitlines()
    blocks: List[Block] = []
    section: Optional[str] = None
    buf: List[str] = []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            blocks.append({"text": text, "page_number": None, "section": section, "kind": "text"})
        buf.clear()

    for line in lines:
        m = _MD_HEADING_RE.match(line.strip())
        if m:
            flush()
            level = len(m.group(1))
            section = m.group(2).strip()
            blocks.append({"text": f"{'#' * level} {section}", "page_number": None, "section": section, "kind": "heading"})
        else:
            buf.append(line)
    flush()
    return blocks


def _extract_plain_blocks(file_path: str) -> List[Block]:
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    blocks = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if para:
            blocks.append({"text": para, "page_number": None, "section": None, "kind": "text"})
    return blocks


def _blocks_from_image(file_path: str, file_type: str | None) -> List[Block]:
    from services.image_ocr_service import extract_image_text

    text = extract_image_text(file_path, file_type)
    return [{"text": text, "page_number": None, "section": None, "kind": "ocr"}]


# ------------------------------------------------------------------ #
# 结构感知分块                                                        #
# ------------------------------------------------------------------ #

def _split_long_text(text: str, max_size: int, overlap: int) -> List[str]:
    """在句子/换行边界切超长文本，尽量保留完整句。"""
    pieces = re.split(r"(?<=[。！？!?;\n])", text)
    out: List[str] = []
    buf = ""
    for piece in pieces:
        if not piece:
            continue
        if len(buf) + len(piece) > max_size and buf:
            out.append(buf)
            tail = buf[-overlap:] if overlap > 0 else ""
            buf = tail + piece
        else:
            buf += piece
    if buf.strip():
        out.append(buf)
    return out or [text]


def chunk_document(blocks: List[Block]) -> List[Dict[str, Any]]:
    """把结构块打包成 chunk，携带 page_number / section / kind 元数据。"""
    target = settings.CHUNK_TARGET_SIZE
    max_size = settings.CHUNK_MAX_SIZE
    overlap = settings.CHUNK_OVERLAP
    min_chars = settings.CHUNK_MIN_CHARS

    # 先按 (page, section) 分组聚合
    groups: List[Dict[str, Any]] = []
    for b in blocks:
        text = (b.get("text") or "").strip()
        if not text:
            continue
        key = (b.get("page_number"), b.get("section"))
        if (
            groups
            and groups[-1]["key"] == key
            and groups[-1]["kind"] == b.get("kind", "text")
            and len(groups[-1]["text"]) < target
            and b.get("kind") != "table"
        ):
            groups[-1]["text"] += ("\n" if not groups[-1]["text"].endswith("\n") else "") + text
        else:
            groups.append(
                {
                    "key": key,
                    "text": text,
                    "page_number": b.get("page_number"),
                    "section": b.get("section"),
                    "kind": b.get("kind") or "text",
                }
            )

    chunks: List[Dict[str, Any]] = []
    for g in groups:
        page_number, section = g["key"]
        if g["kind"] == "table" or len(g["text"]) <= max_size:
            pieces = [g["text"]]
        else:
            pieces = _split_long_text(g["text"], target, overlap)
        for piece in pieces:
            piece = piece.strip()
            if piece:
                chunks.append(
                    {
                        "content": piece,
                        "page_number": page_number,
                        "section": section,
                        "kind": g["kind"],
                    }
                )

    # 小块并入前一块，减少碎片（表格块不参与；跨小节不合并，保持来源可追溯）
    merged: List[Dict[str, Any]] = []
    for chunk in chunks:
        if (
            merged
            and len(chunk["content"]) < min_chars
            and chunk["kind"] != "table"
            and merged[-1]["kind"] != "table"
            and merged[-1]["section"] == chunk["section"]
            and len(merged[-1]["content"]) + len(chunk["content"]) + 1 <= max_size
            and merged[-1]["page_number"] == chunk["page_number"]
        ):
            merged[-1]["content"] += "\n" + chunk["content"]
        else:
            merged.append(chunk)
    return merged


def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """兼容旧接口：纯文本分块（在句子边界切分而非硬截断）。"""
    if not text or not text.strip():
        return []
    blocks: List[Block] = [{"text": text, "page_number": None, "section": None, "kind": "text"}]
    return [c["content"] for c in chunk_document(blocks)]


def count_words(text: str) -> int:
    """Count words, treating each CJK character as one word."""
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]", text))
    latin = len(re.findall(r"\b[a-zA-Z0-9]+\b", text))
    return cjk + latin
