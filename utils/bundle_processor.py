"""
Bundle Processor — TenderSight v3.0

Handles multi-document tender bundles:
  - ZIP extraction with file classification
  - Filename-heuristic document type detection (zero LLM cost)
  - Document hierarchy resolution (Corrigendum > ATC > RFP)
  - BOQ/CSV structured parsing via openpyxl (zero LLM cost)
  - Cross-document conflict detection (zero LLM cost)

Unlike Kriseva's "tender as bundle" (a file organizer), this performs
cross-document intelligence — detecting when an ATC contradicts the RFP,
or when a corrigendum changes eligibility criteria.
"""
import io
import os
import re
import csv
import zipfile
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional Excel support
try:
    import openpyxl
except ImportError:
    openpyxl = None
    logger.info("openpyxl not installed — Excel BOQ parsing disabled")


# ─── Document Type Classification ───

DOC_TYPE_PATTERNS = {
    "rfp": re.compile(
        r"(rfp|nit|tender.?doc|bid.?doc|notice.?invit|request.?for.?proposal)",
        re.IGNORECASE,
    ),
    "boq": re.compile(
        r"(boq|bill.?of.?quant|price.?schedule|financial.?bid|schedule.?of.?quant|rate.?schedule)",
        re.IGNORECASE,
    ),
    "atc": re.compile(
        r"(atc|additional.?term|additional.?cond|special.?cond)",
        re.IGNORECASE,
    ),
    "corrigendum": re.compile(
        r"(corrigendum|corr.?\d|amendment|addendum|errata)",
        re.IGNORECASE,
    ),
    "annexure": re.compile(
        r"(annexure|annex.?\d|format|declaration|proforma|form.?\d)",
        re.IGNORECASE,
    ),
    "spec": re.compile(
        r"(spec|technical.?spec|scope.?of.?work|sow|tech.?req)",
        re.IGNORECASE,
    ),
}

# Procurement document priority (higher number = higher authority)
DOC_PRIORITY = {
    "corrigendum": 60,
    "atc": 50,
    "rfp": 40,
    "spec": 30,
    "boq": 20,
    "annexure": 10,
    "unknown": 0,
}


@dataclass
class BundleDocument:
    """A single document within a tender bundle."""
    filename: str
    doc_type: str  # rfp, boq, atc, corrigendum, annexure, spec, unknown
    raw_bytes: bytes
    extracted_text: str = ""
    metadata: dict = field(default_factory=dict)
    char_count: int = 0
    priority: int = 0

    def __post_init__(self):
        self.priority = DOC_PRIORITY.get(self.doc_type, 0)
        if self.extracted_text:
            self.char_count = len(self.extracted_text)


@dataclass
class ConflictRecord:
    """A detected conflict between two documents."""
    field: str          # e.g., "minimum_turnover"
    doc_a: str          # e.g., "rfp.pdf"
    doc_a_type: str     # e.g., "rfp"
    value_a: str        # e.g., "Rs. 5 Crore"
    doc_b: str          # e.g., "atc.pdf"
    doc_b_type: str     # e.g., "atc"
    value_b: str        # e.g., "Rs. 3 Crore"
    resolution: str     # e.g., "ATC supersedes RFP — effective: Rs. 3 Crore"
    winning_doc: str    # e.g., "atc.pdf"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "doc_a": self.doc_a, "doc_a_type": self.doc_a_type, "value_a": self.value_a,
            "doc_b": self.doc_b, "doc_b_type": self.doc_b_type, "value_b": self.value_b,
            "resolution": self.resolution, "winning_doc": self.winning_doc,
        }


class TenderBundle:
    """
    A collection of classified tender documents with cross-document intelligence.
    """

    def __init__(self, tender_id: str = ""):
        self.tender_id = tender_id
        self.documents: List[BundleDocument] = []
        self.conflicts: List[ConflictRecord] = []
        self.boq_data: Optional[List[dict]] = None  # Parsed BOQ line items

    def add_document(self, doc: BundleDocument):
        self.documents.append(doc)

    def get_by_type(self, doc_type: str) -> List[BundleDocument]:
        return [d for d in self.documents if d.doc_type == doc_type]

    def get_primary_rfp(self) -> Optional[BundleDocument]:
        rfps = self.get_by_type("rfp")
        return rfps[0] if rfps else None

    def get_unified_text(self) -> str:
        """
        Merge all documents into a single text with type-tagged sections.
        Documents are ordered by priority (highest authority first) so that
        the LLM sees overriding documents before base documents.
        """
        sorted_docs = sorted(self.documents, key=lambda d: d.priority, reverse=True)
        sections = []
        for doc in sorted_docs:
            if not doc.extracted_text.strip():
                continue
            type_label = doc.doc_type.upper()
            header = f"{'=' * 60}\nDOCUMENT: {type_label} ({doc.filename})"
            if doc.doc_type == "corrigendum":
                header += "\n[NOTE: CORRIGENDUM — SUPERSEDES ORIGINAL WHERE APPLICABLE]"
            elif doc.doc_type == "atc":
                header += "\n[NOTE: ADDITIONAL TERMS — MAY OVERRIDE STANDARD CONDITIONS]"
            header += f"\n{'=' * 60}"
            sections.append(f"{header}\n{doc.extracted_text}")

        # Append conflict warnings if any
        if self.conflicts:
            conflict_section = f"\n{'=' * 60}\nCROSS-DOCUMENT CONFLICTS DETECTED\n{'=' * 60}\n"
            for c in self.conflicts:
                conflict_section += (
                    f"- {c.field}: {c.doc_a} says '{c.value_a}' vs {c.doc_b} says '{c.value_b}' "
                    f"→ Resolution: {c.resolution}\n"
                )
            sections.append(conflict_section)

        return "\n\n".join(sections)

    def get_summary(self) -> dict:
        type_counts = {}
        for d in self.documents:
            type_counts[d.doc_type] = type_counts.get(d.doc_type, 0) + 1
        return {
            "total_documents": len(self.documents),
            "document_types": type_counts,
            "has_rfp": bool(self.get_by_type("rfp")),
            "has_boq": bool(self.get_by_type("boq")),
            "has_atc": bool(self.get_by_type("atc")),
            "has_corrigendum": bool(self.get_by_type("corrigendum")),
            "conflicts_detected": len(self.conflicts),
            "boq_line_items": len(self.boq_data) if self.boq_data else 0,
            "total_chars": sum(d.char_count for d in self.documents),
        }


# ─── Classification ───

def classify_filename(filename: str) -> str:
    """Classify a document by filename patterns. Zero LLM cost."""
    basename = os.path.splitext(os.path.basename(filename))[0]
    # Replace common separators for matching
    normalized = basename.replace("-", "_").replace(" ", "_")

    for doc_type, pattern in DOC_TYPE_PATTERNS.items():
        if pattern.search(normalized):
            return doc_type

    return "unknown"


def classify_by_content_heuristic(text_preview: str) -> str:
    """
    Classify by reading first ~500 chars of content.
    Still zero LLM cost — uses keyword detection.
    """
    preview = text_preview[:800].lower()

    # BOQ signals
    boq_signals = ["bill of quantities", "sl. no", "item description", "unit rate",
                   "quantity", "total amount", "schedule of rates", "price schedule"]
    if sum(1 for s in boq_signals if s in preview) >= 2:
        return "boq"

    # Corrigendum signals
    if any(s in preview for s in ["corrigendum", "amendment to", "erratum", "addendum"]):
        return "corrigendum"

    # ATC signals
    if any(s in preview for s in ["additional terms", "special conditions",
                                   "additional conditions", "supplementary conditions"]):
        return "atc"

    # Annexure signals
    if any(s in preview for s in ["annexure", "proforma", "format for",
                                   "declaration form", "self-declaration"]):
        return "annexure"

    # Spec signals
    if any(s in preview for s in ["technical specification", "scope of work",
                                   "detailed specifications", "technical requirements"]):
        return "spec"

    # RFP signals (catch-all for main document)
    rfp_signals = ["notice inviting tender", "request for proposal",
                   "eligibility criteria", "bid submission", "tender notice",
                   "invitation for bids", "earnest money"]
    if sum(1 for s in rfp_signals if s in preview) >= 2:
        return "rfp"

    return "unknown"


# ─── ZIP Processing ───

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".xlsx", ".xls", ".docx",
                         ".png", ".jpg", ".jpeg", ".webp"}


def extract_zip(zip_bytes: bytes) -> List[Tuple[str, bytes]]:
    """
    Extract files from a ZIP archive.
    Skips directories, hidden files, macOS resource forks, etc.
    Returns list of (filename, bytes).
    """
    files = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue
                # Skip hidden/system files
                basename = os.path.basename(info.filename)
                if basename.startswith(".") or basename.startswith("__"):
                    continue
                # Skip unsupported extensions
                ext = os.path.splitext(basename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    logger.info(f"Skipping unsupported file: {basename}")
                    continue
                # Extract
                try:
                    data = zf.read(info.filename)
                    files.append((basename, data))
                except Exception as e:
                    logger.warning(f"Failed to extract {info.filename}: {e}")
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file — could not extract")
    return files


def process_zip_to_bundle(zip_bytes: bytes, tender_id: str = "") -> TenderBundle:
    """
    Extract a ZIP file into a classified TenderBundle.
    Classification is filename-heuristic only (zero LLM cost).
    """
    bundle = TenderBundle(tender_id=tender_id)
    files = extract_zip(zip_bytes)

    if not files:
        raise ValueError("ZIP file contains no supported documents")

    for filename, raw_bytes in files:
        doc_type = classify_filename(filename)
        doc = BundleDocument(
            filename=filename,
            doc_type=doc_type,
            raw_bytes=raw_bytes,
        )
        bundle.add_document(doc)
        logger.info(f"Bundle: {filename} → classified as [{doc_type}]")

    # If no RFP was identified, promote the largest unknown/unclassified PDF
    if not bundle.get_by_type("rfp"):
        unknowns = [d for d in bundle.documents if d.doc_type == "unknown"]
        pdfs = [d for d in unknowns if d.filename.lower().endswith(".pdf")]
        if pdfs:
            largest = max(pdfs, key=lambda d: len(d.raw_bytes))
            largest.doc_type = "rfp"
            largest.priority = DOC_PRIORITY["rfp"]
            logger.info(f"Auto-promoted '{largest.filename}' to RFP (largest unclassified PDF)")

    return bundle


# ─── BOQ Parsing (Zero LLM Cost) ───

def parse_boq_excel(file_bytes: bytes, filename: str) -> List[dict]:
    """
    Parse a BOQ Excel file into structured line items.
    Returns list of dicts with keys: item_no, description, unit, quantity, rate, amount.
    """
    if openpyxl is None:
        logger.warning("openpyxl not installed — cannot parse Excel BOQ")
        return []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        if len(rows) < 2:
            return []

        # Try to detect header row
        header_row = None
        for i, row in enumerate(rows[:5]):
            row_text = " ".join(str(c or "").lower() for c in row)
            if any(kw in row_text for kw in ["description", "item", "quantity", "rate", "amount"]):
                header_row = i
                break

        if header_row is None:
            header_row = 0

        headers = [str(c or "").strip().lower() for c in rows[header_row]]
        items = []

        for row in rows[header_row + 1:]:
            if not any(row):
                continue
            item = {}
            for j, val in enumerate(row):
                if j < len(headers):
                    item[headers[j]] = val
            # Try to normalize to standard keys
            normalized = _normalize_boq_item(item)
            if normalized:
                items.append(normalized)

        return items

    except Exception as e:
        logger.error(f"BOQ Excel parsing failed for {filename}: {e}")
        return []


def parse_boq_csv(file_bytes: bytes, filename: str) -> List[dict]:
    """Parse a BOQ CSV file into structured line items."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        items = []
        for row in reader:
            normalized = _normalize_boq_item(row)
            if normalized:
                items.append(normalized)
        return items
    except Exception as e:
        logger.error(f"BOQ CSV parsing failed for {filename}: {e}")
        return []


def _normalize_boq_item(raw: dict) -> Optional[dict]:
    """Normalize a BOQ row to standard field names."""
    def _find(keys, d):
        for k in keys:
            for dk, dv in d.items():
                if k in str(dk).lower():
                    return dv
        return None

    desc = _find(["description", "item", "particulars", "name", "work"], raw)
    if not desc or not str(desc).strip():
        return None

    qty = _find(["quantity", "qty", "nos", "number"], raw)
    unit = _find(["unit", "uom"], raw)
    rate = _find(["rate", "unit price", "price"], raw)
    amount = _find(["amount", "total", "value"], raw)

    def _to_float(v):
        if v is None:
            return None
        try:
            return float(str(v).replace(",", "").replace("Rs.", "").strip())
        except (ValueError, TypeError):
            return None

    return {
        "description": str(desc).strip(),
        "quantity": _to_float(qty),
        "unit": str(unit or "").strip(),
        "rate": _to_float(rate),
        "amount": _to_float(amount),
    }


def process_boq_in_bundle(bundle: TenderBundle):
    """Parse any BOQ documents in the bundle. Zero LLM cost."""
    for doc in bundle.get_by_type("boq"):
        ext = os.path.splitext(doc.filename)[1].lower()
        items = []
        if ext in (".xlsx", ".xls"):
            items = parse_boq_excel(doc.raw_bytes, doc.filename)
        elif ext == ".csv":
            items = parse_boq_csv(doc.raw_bytes, doc.filename)

        if items:
            bundle.boq_data = items
            # Also generate a text representation for the LLM
            boq_text = "BILL OF QUANTITIES — STRUCTURED DATA\n"
            boq_text += f"{'No.':<6}{'Description':<50}{'Qty':<10}{'Unit':<10}{'Rate':<15}{'Amount':<15}\n"
            boq_text += "-" * 106 + "\n"
            total = 0.0
            for i, item in enumerate(items, 1):
                amt = item.get("amount") or 0
                total += amt
                boq_text += (
                    f"{i:<6}"
                    f"{str(item.get('description', ''))[:48]:<50}"
                    f"{item.get('quantity') or '':<10}"
                    f"{str(item.get('unit', '')):<10}"
                    f"{item.get('rate') or '':<15}"
                    f"{amt:<15.2f}\n"
                )
            boq_text += "-" * 106 + "\n"
            boq_text += f"{'TOTAL':>76}{total:<15.2f}\n"
            doc.extracted_text = boq_text
            doc.char_count = len(boq_text)
            logger.info(f"Parsed {len(items)} BOQ line items, total: {total:,.2f}")


# ─── Multi-file Processing (non-ZIP) ───

def process_multiple_files(
    files: List[Tuple[str, bytes]],
    doc_types: Optional[Dict[str, str]] = None,
    tender_id: str = "",
) -> TenderBundle:
    """
    Process multiple individually uploaded files into a bundle.
    doc_types: optional {filename: doc_type} overrides from the user.
    """
    bundle = TenderBundle(tender_id=tender_id)
    for filename, raw_bytes in files:
        # Use user-provided type, or fall back to filename heuristics
        if doc_types and filename in doc_types:
            doc_type = doc_types[filename]
        else:
            doc_type = classify_filename(filename)
        doc = BundleDocument(
            filename=filename,
            doc_type=doc_type,
            raw_bytes=raw_bytes,
        )
        bundle.add_document(doc)
    return bundle
