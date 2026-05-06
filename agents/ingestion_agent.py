"""
Smart Document Ingestion Agent — Handles all document types with intelligent fallback.

Pipeline:
  .txt  → direct UTF-8 decode
  .pdf  → PyPDF extract → if <100 chars → Gemini 2.5 Flash VLM → if unavailable → NVIDIA VLM
  image → Gemini 2.5 Flash VLM → if unavailable → NVIDIA VLM
"""
import io
import os
import logging
import mimetypes
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Optional imports (graceful degradation) ───
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

AUTO_NATIVE_TEXT_THRESHOLD = 100  # Minimum chars to consider PDF "parsable"

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _extract_pdf_text(file_bytes: bytes) -> Tuple[str, int]:
    """Extract text from PDF using PyPDF. Returns (text, page_count)."""
    if pypdf is None:
        logger.warning("pypdf not installed — cannot extract native PDF text")
        return "", 0
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = len(reader.pages)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts), pages
    except Exception as e:
        logger.error("PyPDF extraction failed: %s", e)
        return "", 0


def _count_pdf_pages(file_bytes: bytes) -> int:
    """Count pages in a PDF."""
    if pypdf is None:
        return 0
    try:
        return len(pypdf.PdfReader(io.BytesIO(file_bytes)).pages)
    except Exception:
        return 0


def _extract_with_gemini(file_bytes: bytes, mime_type: str, filename: str) -> Tuple[str, float, str]:
    """
    Extract text from a document using Gemini 2.5 Flash VLM.
    Returns (text, confidence, engine_name).
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if genai is None or genai_types is None or not api_key:
        return "", 0.0, "gemini_unavailable"

    client = genai.Client(api_key=api_key)
    prompt = (
        "Extract ALL visible text from this document as plain text.\n"
        "Preserve page order, headings, table rows, labels, values, and numbering.\n"
        "Do not summarize, do not explain, and do not add commentary.\n"
        "If a token is unreadable, replace it with [unclear]."
    )

    import asyncio

    async def _call():
        import time
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                        prompt,
                    ],
                )
                text = (response.text or "").strip()
                if text:
                    return text, 0.88, "gemini-2.5-flash"
            except Exception as e:
                logger.warning("Gemini VLM attempt %d failed: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        return "", 0.0, "gemini_failed"

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _call()).result()
        return loop.run_until_complete(_call())
    except RuntimeError:
        return asyncio.run(_call())


def _extract_with_nvidia_vlm(file_bytes: bytes, filename: str, api_key: str = None) -> Tuple[str, float, str]:
    """
    Fallback: Extract text using NVIDIA VLM (page-by-page for PDFs).
    Returns (text, confidence, engine_name).
    """
    from config import VLM_MODEL_NAME, NVIDIA_API_KEY
    key = api_key or NVIDIA_API_KEY
    if not key:
        return "", 0.0, "nvidia_unavailable"

    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        from langchain_core.messages import HumanMessage
        import base64

        vlm = ChatNVIDIA(model=VLM_MODEL_NAME, nvidia_api_key=key, max_tokens=4096)
        prompt = "Extract all text from this document image. Preserve structure, tables, headings."

        # For PDFs, convert pages to images
        if filename.lower().endswith(".pdf"):
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                all_text = []
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    b64 = base64.b64encode(img_bytes).decode()
                    msg = HumanMessage(content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ])
                    response = vlm.invoke([msg])
                    all_text.append(f"--- PAGE {i+1} ---\n{str(response.content).strip()}")
                doc.close()
                return "\n\n".join(all_text), 0.80, "nvidia-vlm"
            except ImportError:
                logger.warning("PyMuPDF not installed — cannot convert PDF to images for VLM")
                return "", 0.0, "nvidia_no_pymupdf"
        else:
            # Direct image
            b64 = base64.b64encode(file_bytes).decode()
            mime = mimetypes.guess_type(filename)[0] or "image/png"
            msg = HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ])
            response = vlm.invoke([msg])
            return str(response.content).strip(), 0.80, "nvidia-vlm"
    except Exception as e:
        logger.error("NVIDIA VLM extraction failed: %s", e)
        return "", 0.0, "nvidia_failed"


def _guess_mime_type(filename: str) -> str:
    """Guess MIME type from filename."""
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    if filename.lower().endswith(".pdf"):
        return "application/pdf"
    return "application/octet-stream"


def ingest_document(
    file_bytes: bytes,
    filename: str,
    api_key: str = None,
    document_mode: str = "auto",
    progress_callback=None,
) -> dict:
    """
    Smart document ingestion with intelligent fallback.

    Modes:
      - "auto": PyPDF → if too little text → Gemini VLM → NVIDIA VLM
      - "structured": PyPDF only (fast, text-based PDFs)
      - "visual": Force VLM extraction (scanned/image docs)

    Returns:
      {"raw_text": str, "pages": int, "ocr_engine": str, "confidence": float}
    """
    filename_lower = filename.lower()
    mime_type = _guess_mime_type(filename)

    # ─── Plain text ───
    if filename_lower.endswith(".txt"):
        if progress_callback:
            progress_callback("📄 Reading text file...")
        try:
            text = file_bytes.decode("utf-8")
            return {"raw_text": text, "pages": 1, "ocr_engine": "plain_text", "confidence": 1.0}
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
            return {"raw_text": text, "pages": 1, "ocr_engine": "plain_text_fallback", "confidence": 0.9}

    # ─── PDF ───
    if filename_lower.endswith(".pdf"):
        if progress_callback:
            progress_callback("📋 Processing PDF...")

        # Step 1: Try PyPDF native extraction
        if document_mode in ("auto", "structured"):
            if progress_callback:
                progress_callback("📋 Extracting text from PDF...")
            native_text, pages = _extract_pdf_text(file_bytes)

            if document_mode == "structured":
                return {"raw_text": native_text, "pages": pages, "ocr_engine": "pypdf", "confidence": 0.95}

            # Auto mode: check if enough text was extracted
            if len(native_text.strip()) >= AUTO_NATIVE_TEXT_THRESHOLD:
                if progress_callback:
                    progress_callback(f"✅ Extracted {len(native_text)} chars from PDF")
                return {"raw_text": native_text, "pages": pages, "ocr_engine": "pypdf", "confidence": 0.95}

            if progress_callback:
                progress_callback("📷 PDF has little text — trying VLM extraction...")

        # Step 2: Fallback to Gemini VLM
        if progress_callback:
            progress_callback("🔍 Using Vision to read document...")
        pages = _count_pdf_pages(file_bytes)
        text, confidence, engine = _extract_with_gemini(file_bytes, "application/pdf", filename)
        if text.strip():
            if progress_callback:
                progress_callback(f"✅ VLM extracted {len(text)} chars")
            return {"raw_text": text, "pages": pages, "ocr_engine": engine, "confidence": confidence}

        # Step 3: Fallback to NVIDIA VLM
        if progress_callback:
            progress_callback("🔄 Trying NVIDIA Vision fallback...")
        text, confidence, engine = _extract_with_nvidia_vlm(file_bytes, filename, api_key)
        if text.strip():
            return {"raw_text": text, "pages": pages, "ocr_engine": engine, "confidence": confidence}

        return {"raw_text": "Could not extract text from this PDF.", "pages": pages, "ocr_engine": "none", "confidence": 0.0}

    # ─── Images ───
    if mime_type in SUPPORTED_IMAGE_TYPES:
        if progress_callback:
            progress_callback("🖼️ Processing image document...")

        text, confidence, engine = _extract_with_gemini(file_bytes, mime_type, filename)
        if text.strip():
            return {"raw_text": text, "pages": 1, "ocr_engine": engine, "confidence": confidence}

        text, confidence, engine = _extract_with_nvidia_vlm(file_bytes, filename, api_key)
        if text.strip():
            return {"raw_text": text, "pages": 1, "ocr_engine": engine, "confidence": confidence}

        return {"raw_text": "Could not extract text from image.", "pages": 1, "ocr_engine": "none", "confidence": 0.0}

    # ─── Unknown format — try as text ───
    try:
        text = file_bytes.decode("utf-8")
        return {"raw_text": text, "pages": 1, "ocr_engine": "plain_text", "confidence": 0.9}
    except UnicodeDecodeError:
        return {"raw_text": "Unsupported file format.", "pages": 0, "ocr_engine": "none", "confidence": 0.0}
