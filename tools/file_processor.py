"""
Anju AI — File Processor & Intelligence Engine
Scans, extracts, and understands uploaded files.
Supports: Images, PDFs, DOCX, XLSX, PPTX, TXT, CSV, JSON, Code files
"""

import os
import base64
import json
import mimetypes
from datetime import datetime

# ── Upload Directory ───────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
MODIFIED_DIR = os.path.join(UPLOAD_DIR, "modified")

def ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(MODIFIED_DIR, exist_ok=True)

# ── File Type Detection ────────────────────────────────────────────────────────
IMAGE_EXTS    = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DOCUMENT_EXTS = {".pdf"}
WORD_EXTS     = {".docx", ".doc"}
EXCEL_EXTS    = {".xlsx", ".xls"}
PPT_EXTS      = {".pptx", ".ppt"}
TEXT_EXTS     = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".csv", ".json",
                 ".yaml", ".yml", ".xml", ".ini", ".toml", ".sh", ".bat", ".c", ".cpp",
                 ".java", ".rs", ".go", ".rb", ".php", ".sql", ".log"}

def get_file_category(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTS:    return "image"
    if ext in DOCUMENT_EXTS: return "pdf"
    if ext in WORD_EXTS:     return "word"
    if ext in EXCEL_EXTS:    return "excel"
    if ext in PPT_EXTS:      return "powerpoint"
    if ext in TEXT_EXTS:     return "text"
    return "unknown"

# ── Icon Mapper ────────────────────────────────────────────────────────────────
CATEGORY_ICONS = {
    "image":      "🖼️",
    "pdf":        "📄",
    "word":       "📝",
    "excel":      "📊",
    "powerpoint": "📑",
    "text":       "📃",
    "unknown":    "📎",
}

def get_file_icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📎")

# ── Extraction Engine ──────────────────────────────────────────────────────────

def extract_image(filepath: str) -> dict:
    """
    Uses Gemini Vision to analyze and fully describe the image.
    Returns rich textual extraction.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured.", "content": ""}

    try:
        from google import genai
        ext = os.path.splitext(filepath)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".gif": "image/gif", ".bmp": "image/bmp"
        }
        mime_type = mime_map.get(ext, "image/png")

        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        client = genai.Client(api_key=api_key)
        prompt = (
            "You are a professional image analyst for Anju AI. "
            "Analyze this image completely and extract ALL visible text, data, charts, "
            "labels, colors, objects, people, text blocks, numbers, tables, and meaningful details. "
            "Format your response clearly with sections: "
            "[Text Found], [Objects & Scene], [Data & Numbers], [Colors & Design], [Overall Summary]. "
            "Be extremely thorough and detailed."
        )
        contents = [
            prompt,
            {"inline_data": {"mime_type": mime_type, "data": image_data}}
        ]
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents
        )
        return {
            "content": response.text,
            "preview": response.text[:300] + "..." if len(response.text) > 300 else response.text,
            "error": None
        }
    except Exception as e:
        return {"content": f"Vision analysis failed: {e}", "preview": "", "error": str(e)}


def extract_pdf(filepath: str) -> dict:
    """
    Extracts text from PDF using pypdf. Falls back to Gemini vision for image-heavy PDFs.
    """
    content_parts = []

    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                content_parts.append(f"--- Page {i+1} ---\n{text.strip()}")

        if content_parts:
            full_text = "\n\n".join(content_parts)
            return {
                "content": full_text,
                "preview": full_text[:400] + "..." if len(full_text) > 400 else full_text,
                "pages": total_pages,
                "error": None
            }
        else:
            # Image-heavy PDF — use Gemini vision on first page
            return _extract_pdf_with_vision(filepath)

    except ImportError:
        # pypdf not installed — try with vision
        return _extract_pdf_with_vision(filepath)
    except Exception as e:
        return {"content": f"PDF extraction failed: {e}", "preview": "", "pages": 0, "error": str(e)}


def _extract_pdf_with_vision(filepath: str) -> dict:
    """Fallback: convert PDF page to image and use Gemini Vision."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        pages_text = []

        for page_num in range(min(len(doc), 5)):  # Max 5 pages via vision
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_path = os.path.join(UPLOAD_DIR, f"_pdf_page_{page_num}.png")
            pix.save(img_path)

            result = extract_image(img_path)
            if result.get("content"):
                pages_text.append(f"--- Page {page_num+1} ---\n{result['content']}")

            # Cleanup temp page image
            try: os.remove(img_path)
            except: pass

        doc.close()
        full_text = "\n\n".join(pages_text) if pages_text else "No extractable content found in PDF."
        return {
            "content": full_text,
            "preview": full_text[:400] + "..." if len(full_text) > 400 else full_text,
            "pages": len(pages_text),
            "error": None
        }
    except Exception as e:
        return {
            "content": f"PDF vision extraction failed: {e}",
            "preview": "",
            "pages": 0,
            "error": str(e)
        }


def extract_word(filepath: str) -> dict:
    """Extracts all text, tables, and headings from DOCX files."""
    try:
        from docx import Document
        doc = Document(filepath)
        content_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                if para.style.name.startswith("Heading"):
                    content_parts.append(f"\n## {para.text.strip()}")
                else:
                    content_parts.append(para.text.strip())

        # Extract tables
        for i, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(cells))
            if table_rows:
                content_parts.append(f"\n[Table {i+1}]\n" + "\n".join(table_rows))

        full_text = "\n".join(content_parts)
        if not full_text.strip():
            full_text = "The document appears to be empty or contains only non-text content."

        return {
            "content": full_text,
            "preview": full_text[:400] + "..." if len(full_text) > 400 else full_text,
            "error": None
        }
    except ImportError:
        return {"content": "python-docx is not installed. Run: pip install python-docx", "preview": "", "error": "missing_lib"}
    except Exception as e:
        return {"content": f"Word extraction failed: {e}", "preview": "", "error": str(e)}


def extract_excel(filepath: str) -> dict:
    """Extracts all sheets and rows from XLSX/XLS files."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        content_parts = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                row_vals = [str(cell) if cell is not None else "" for cell in row]
                if any(v.strip() for v in row_vals):
                    rows_data.append(" | ".join(row_vals))

            if rows_data:
                content_parts.append(f"=== Sheet: {sheet_name} ===\n" + "\n".join(rows_data))

        wb.close()
        full_text = "\n\n".join(content_parts) if content_parts else "Spreadsheet appears to be empty."

        return {
            "content": full_text,
            "preview": full_text[:400] + "..." if len(full_text) > 400 else full_text,
            "sheets": len(wb.sheetnames) if content_parts else 0,
            "error": None
        }
    except ImportError:
        return {"content": "openpyxl is not installed. Run: pip install openpyxl", "preview": "", "error": "missing_lib"}
    except Exception as e:
        return {"content": f"Excel extraction failed: {e}", "preview": "", "error": str(e)}


def extract_powerpoint(filepath: str) -> dict:
    """Extracts all slide text, titles, and notes from PPTX files."""
    try:
        from pptx import Presentation
        prs = Presentation(filepath)
        content_parts = []

        for i, slide in enumerate(prs.slides):
            slide_parts = [f"--- Slide {i+1} ---"]
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_parts.append(shape.text.strip())
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_parts.append(f"[Notes]: {notes}")
            if len(slide_parts) > 1:
                content_parts.append("\n".join(slide_parts))

        full_text = "\n\n".join(content_parts) if content_parts else "Presentation appears to be empty."

        return {
            "content": full_text,
            "preview": full_text[:400] + "..." if len(full_text) > 400 else full_text,
            "slides": len(prs.slides),
            "error": None
        }
    except ImportError:
        return {"content": "python-pptx is not installed. Run: pip install python-pptx", "preview": "", "error": "missing_lib"}
    except Exception as e:
        return {"content": f"PowerPoint extraction failed: {e}", "preview": "", "error": str(e)}


def extract_text(filepath: str) -> dict:
    """Reads plain text / code / CSV / JSON files directly."""
    try:
        # Try UTF-8 first, then latin-1 fallback
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            return {"content": "Unable to decode file — may be binary.", "preview": "", "error": "encoding"}

        # If JSON, pretty-print it
        if filepath.endswith(".json"):
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)
            except: pass

        preview = content[:400] + "..." if len(content) > 400 else content
        return {
            "content": content,
            "preview": preview,
            "lines": content.count("\n") + 1,
            "chars": len(content),
            "error": None
        }
    except Exception as e:
        return {"content": f"Text extraction failed: {e}", "preview": "", "error": str(e)}


# ── Master Scan Function ───────────────────────────────────────────────────────

def scan_file(filepath: str) -> dict:
    """
    Master function — detects file type and runs appropriate extractor.
    Returns a structured result dict consumed by the dashboard & brain.
    """
    ensure_dirs()

    if not os.path.exists(filepath):
        return {
            "success": False,
            "error": f"File not found: {filepath}",
            "filename": os.path.basename(filepath),
            "category": "unknown",
            "content": "",
            "preview": ""
        }

    filename = os.path.basename(filepath)
    category = get_file_category(filepath)
    icon = get_file_icon(category)
    file_size = os.path.getsize(filepath)

    print(f"[FileProcessor] Scanning {icon} {filename} ({category}, {file_size} bytes)...")

    if category == "image":
        result = extract_image(filepath)
    elif category == "pdf":
        result = extract_pdf(filepath)
    elif category == "word":
        result = extract_word(filepath)
    elif category == "excel":
        result = extract_excel(filepath)
    elif category == "powerpoint":
        result = extract_powerpoint(filepath)
    elif category == "text":
        result = extract_text(filepath)
    else:
        # Try as text fallback
        result = extract_text(filepath)
        if result.get("error"):
            result = {"content": "Unsupported file type. Anju cannot read this format.", "preview": "", "error": "unsupported"}

    return {
        "success": not bool(result.get("error")),
        "filename": filename,
        "filepath": filepath,
        "category": category,
        "icon": icon,
        "file_size": file_size,
        "content": result.get("content", ""),
        "preview": result.get("preview", result.get("content", "")[:300]),
        "error": result.get("error"),
        "scanned_at": datetime.now().isoformat(),
        # Extra metadata by type
        "pages": result.get("pages"),
        "slides": result.get("slides"),
        "sheets": result.get("sheets"),
        "lines": result.get("lines"),
    }


# ── File Modification Engine ───────────────────────────────────────────────────

def save_modified_file(original_filename: str, new_content: str, suffix: str = "_modified") -> str:
    """
    Saves modified content to the modified/ directory.
    Returns the relative path for serving via Flask.
    """
    ensure_dirs()

    name, ext = os.path.splitext(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{name}{suffix}_{timestamp}{ext if ext else '.txt'}"
    output_path = os.path.join(MODIFIED_DIR, new_filename)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[FileProcessor] Modified file saved: {output_path}")
        return f"uploads/modified/{new_filename}"
    except Exception as e:
        print(f"[FileProcessor] Save failed: {e}")
        return ""


def get_context_injection(scan_result: dict) -> str:
    """
    Formats the file scan result as a context injection string for Anju's brain.
    This is injected into the Gemini system prompt so Anju can reason about the file.
    """
    if not scan_result or not scan_result.get("success"):
        return ""

    fname = scan_result.get("filename", "unknown")
    category = scan_result.get("category", "unknown")
    icon = scan_result.get("icon", "📎")
    content = scan_result.get("content", "")

    # Truncate very large files to prevent token overflow
    MAX_CONTENT_CHARS = 8000
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + f"\n\n[... Content truncated at {MAX_CONTENT_CHARS} chars for context window. Full content is available in the upload.]"

    extra = ""
    if scan_result.get("pages"):
        extra += f" ({scan_result['pages']} pages)"
    elif scan_result.get("slides"):
        extra += f" ({scan_result['slides']} slides)"
    elif scan_result.get("sheets"):
        extra += f" ({scan_result['sheets']} sheets)"
    elif scan_result.get("lines"):
        extra += f" ({scan_result['lines']} lines)"

    return f"""
===== UPLOADED FILE CONTEXT =====
{icon} File: {fname} ({category}{extra})
Scanned at: {scan_result.get('scanned_at', 'unknown')}
Filepath: {scan_result.get('filepath', '')}

EXTRACTED CONTENT:
{content}
===== END OF FILE CONTEXT =====
"""
