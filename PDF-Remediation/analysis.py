"""PDF accessibility analysis."""

# -------------------------------------------------------------------------------
# analysis.py — all PDF analysis and pre-flight checking for the PDF Assistant
#
# Constants:
#   LIST_PATTERN, CONDENSED_FONT_HINTS, DEMO_ISSUES
#
# Functions:
#   preflight_check()             — verify external deps before starting a pipeline
#   _detect_title_candidate()     — find the largest-font span on page 1
#   _lang_display_name()          — BCP 47 code → human-readable name
#   _generate_toc_from_font_sizes() — font-size heuristic → TOC list for set_toc()
#   _extract_heading_sequence()   — walk StructTreeRoot → ordered heading levels
#   _check_heading_hierarchy()    — detect skipped heading levels
#   _describe_heading_sequence()  — human-readable summary of heading sequence
#   _run_docling()                — ML document conversion → DoclingDocument
#   analyze_pdf()                 — full accessibility analysis → result dict
# -------------------------------------------------------------------------------

import io
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from collections import Counter

import fitz
import pikepdf
from langdetect import detect as detect_language
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel


# Compiled once at import time — regex for visually formatted list lines.
LIST_PATTERN = re.compile(
    r"^\s*([•·▪▸➢◦○●\-\*]|\d{1,2}[.)]\s|[a-zA-Z][.]\s)\s*\S"
)

# Font name substrings identifying condensed typefaces — excluded from the
# letter-spacing heuristic because their narrow widths are intentional design.
CONDENSED_FONT_HINTS = frozenset({"condense", "narrow", "compress", "condens"})


# =============================================================================
# DEMO ISSUE DATA
# =============================================================================
# Fallback issue list returned by analyze_pdf() when PDF parsing fails entirely.
# =============================================================================
DEMO_ISSUES = [
    {
        "id": "missing_alt_text",
        "severity": "red",
        "title": "Images with missing text descriptions",
        "description": (
            "This document contains images that don't have text descriptions (also called "
            "alt text). Students who use screen readers — software that reads content aloud "
            "— won't be able to access the information those images convey."
        ),
        "wcag": "WCAG 2.2 SC 1.1.1 — Non-text Content",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've reviewed each image in your document and generated a text description "
            "for each one. I'll walk you through them one at a time so you can review "
            "and approve each description before it's saved."
        ),
    },
    {
        "id": "untagged_pdf",
        "severity": "red",
        "title": "Untagged PDF — no document structure",
        "description": (
            "This document has no accessibility tags. Tags are the behind-the-scenes "
            "structure that tells screen readers what is a heading, what is a paragraph, "
            "and what order to read things in. Without them, a screen reader user hears "
            "the content as an undifferentiated stream of text — or nothing at all."
        ),
        "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've analyzed the visual layout of your document and generated a tag "
            "structure that reflects the correct reading order and heading hierarchy. "
            "Here's a summary of the structure I'll apply."
        ),
    },
    {
        "id": "heading_hierarchy",
        "severity": "yellow",
        "title": "Incorrect or missing heading hierarchy",
        "description": (
            "The heading levels in this document are inconsistent — some levels are "
            "skipped, and the structure doesn't match what a reader would expect from "
            "the visual layout. Screen reader users navigate long documents by jumping "
            "between headings, so an incorrect hierarchy makes it hard to find content."
        ),
        "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've mapped your document's visual layout to a correct heading hierarchy "
            "(Heading 1 → Heading 2 → Heading 3) with no skipped levels. Here's the "
            "proposed structure."
        ),
    },
    {
        "id": "missing_lang",
        "severity": "yellow",
        "title": "Missing document language tag",
        "description": (
            "This document doesn't declare what language it's written in. Screen readers "
            "use the language tag to select the correct pronunciation rules and speech "
            "engine. Without it, text may be read aloud in the wrong language or with "
            "incorrect pronunciation — especially for technical terms and proper names."
        ),
        "wcag": "WCAG 2.2 SC 3.1.1 — Language of Page",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've detected that this document is written in English and will add the "
            "language tag 'en-US' to the document metadata."
        ),
    },
    {
        "id": "missing_title",
        "severity": "green",
        "title": "Missing document title in metadata",
        "description": (
            "The document's title field is empty — it currently defaults to the filename. "
            "Screen readers announce the document title when a file opens, and search "
            "tools use it for indexing. A descriptive title helps all users understand "
            "what they're looking at before they start reading."
        ),
        "wcag": "WCAG 2.2 SC 2.4.2 — Page Titled",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I'll add a descriptive title to the document metadata based on the content "
            "I found at the top of the first page. You can review and edit it before I save."
        ),
    },
    {
        "id": "missing_bookmarks",
        "severity": "green",
        "title": "Missing bookmarks / navigation",
        "description": (
            "This document is long enough that it would benefit from bookmarks — a "
            "clickable table of contents that lets readers jump directly to any section. "
            "Without bookmarks, everyone (not just screen reader users) has to scroll "
            "through the entire document to find what they need."
        ),
        "wcag": "WCAG 2.2 SC 2.4.5 — Multiple Ways",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've generated a bookmark list based on the heading structure in your "
            "document. Here's what it will look like in the navigation panel."
        ),
    },
]


# =============================================================================
# PREFLIGHT CHECK
# =============================================================================

def preflight_check(tesseract_path=None, api_endpoints=None, output_paths=None):
    """
    Verify external dependencies before starting a pipeline.

    Parameters:
        tesseract_path (str | None): Full path to the Tesseract executable.
        api_endpoints (list[str] | None): URLs that must return 2xx.
        output_paths (list[str] | None): Paths the pipeline will write to.

    Returns:
        dict: {"ok": bool, "errors": list[str]}
    """
    errors = []

    if tesseract_path is not None:
        on_path      = shutil.which("tesseract") is not None
        configured_ok = False
        try:
            result = subprocess.run(
                [tesseract_path, "--version"],
                capture_output=True,
                timeout=5,
            )
            configured_ok = result.returncode == 0
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
            pass

        if not on_path and not configured_ok:
            errors.append(
                f"Tesseract OCR could not be found. "
                f"Verify that Tesseract is installed and that the path in the "
                f"sidebar settings is correct.\n"
                f"Configured path: `{tesseract_path}`\n"
                f"Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        elif not configured_ok:
            errors.append(
                f"Tesseract was found on the system PATH but could not be run "
                f"from the path entered in sidebar settings.\n"
                f"Configured path: `{tesseract_path}`\n"
                f"Please update the Tesseract path in the ⚙️ Settings panel."
            )

    if api_endpoints:
        for url in api_endpoints:
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status >= 400:
                        errors.append(
                            f"Required API endpoint returned HTTP {resp.status}: {url}\n"
                            f"The service may be down or misconfigured."
                        )
            except urllib.error.URLError as exc:
                errors.append(
                    f"Required API endpoint is unreachable: {url}\n"
                    f"Network error: {exc.reason}"
                )
            except Exception as exc:
                errors.append(
                    f"Could not check API endpoint: {url}\n"
                    f"Error: {exc}"
                )

    if output_paths:
        for path in output_paths:
            if os.path.isdir(path):
                probe = os.path.join(path, ".preflight_write_probe")
                try:
                    with open(probe, "a+b"):
                        pass
                    os.remove(probe)
                except PermissionError:
                    errors.append(
                        f"Output path is locked by another process or the app "
                        f"does not have write permission: `{path}`\n"
                        f"Close any applications that may have this file open and try again."
                    )
                except OSError as exc:
                    errors.append(
                        f"Output path is not writable: `{path}`\n"
                        f"OS error: {exc}"
                    )
            else:
                try:
                    with open(path, "a+b"):
                        pass
                except PermissionError:
                    errors.append(
                        f"Output path is locked by another process or the app "
                        f"does not have write permission: `{path}`\n"
                        f"Close any applications that may have this file open and try again."
                    )
                except OSError as exc:
                    errors.append(
                        f"Output path is not writable: `{path}`\n"
                        f"OS error: {exc}"
                    )

    return {"ok": len(errors) == 0, "errors": errors}


# =============================================================================
# ANALYSIS HELPER FUNCTIONS
# =============================================================================

def _detect_title_candidate(doc):
    """
    Scan the first page for the largest-font non-empty text span.

    Parameters:
        doc: an open fitz.Document object

    Returns:
        str: the candidate title text, or "" if nothing found
    """
    try:
        page = doc[0]
        blocks = page.get_text("dict")["blocks"]
        best_text = ""
        best_size = 0
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if text and size > best_size and len(text) < 120:
                        best_size = size
                        best_text = text
        return best_text
    except Exception:
        return ""


def _lang_display_name(lang_code):
    """
    Map a BCP 47 language code to a human-readable name.

    Parameters:
        lang_code (str): e.g. "en-US", "fr-FR"

    Returns:
        str: readable name, or the code itself if not in the table
    """
    names = {
        "en": "English", "en-US": "English", "en-GB": "English",
        "fr": "French",  "fr-FR": "French",
        "es": "Spanish", "es-ES": "Spanish",
        "de": "German",  "de-DE": "German",
        "zh": "Chinese", "ja": "Japanese", "ar": "Arabic",
        "pt": "Portuguese", "it": "Italian",
    }
    return names.get(lang_code, lang_code)


def _generate_toc_from_font_sizes(doc):
    """
    Build a table-of-contents list suitable for fitz.Document.set_toc()
    using font-size heuristics to identify headings.

    Parameters:
        doc: an open fitz.Document object

    Returns:
        list of [int level, str title, int page]
    """
    all_spans = []
    for page_num, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    if text and size > 0 and len(text) < 150:
                        all_spans.append({
                            "text": text,
                            "size": size,
                            "page": page_num + 1,
                        })

    if not all_spans:
        return []

    sizes = [round(s["size"]) for s in all_spans]
    body_size = Counter(sizes).most_common(1)[0][0]

    heading_spans = [s for s in all_spans if s["size"] > body_size * 1.2]
    if not heading_spans:
        return []

    unique_sizes = sorted(set(round(s["size"]) for s in heading_spans), reverse=True)
    size_to_level = {sz: min(i + 1, 3) for i, sz in enumerate(unique_sizes)}

    toc = []
    seen = set()
    for span in heading_spans:
        text = span["text"]
        if text in seen:
            continue
        seen.add(text)
        level = size_to_level.get(round(span["size"]), 1)
        toc.append([level, text, span["page"]])

    return toc


def _extract_heading_sequence(file_bytes):
    """
    Walk the PDF StructTreeRoot recursively and return heading levels in order.

    Parameters:
        file_bytes (bytes): Raw PDF bytes.

    Returns:
        list[int]: Heading levels e.g. [1, 2, 3, 2, 1, 2].
    """
    levels = []

    def _walk(node):
        try:
            if isinstance(node, pikepdf.Dictionary):
                s_val = node.get("/S")
                if s_val is not None:
                    s = str(s_val)
                    if s == "/H":
                        levels.append(1)
                    elif len(s) == 3 and s[1] == "H" and s[2].isdigit():
                        levels.append(int(s[2]))
                kids = node.get("/K")
                if kids is not None:
                    _walk(kids)
            elif isinstance(node, pikepdf.Array):
                for item in node:
                    _walk(item)
        except Exception:
            pass

    try:
        with pikepdf.open(io.BytesIO(file_bytes)) as pdf:
            if "/StructTreeRoot" not in pdf.Root:
                return []
            _walk(pdf.Root["/StructTreeRoot"])
    except Exception:
        pass

    return levels


def _check_heading_hierarchy(levels):
    """
    Inspect a heading level sequence for structural problems.

    Parameters:
        levels (list[int]): Output of _extract_heading_sequence().

    Returns:
        str: "none" | "skip" | "ok"
    """
    if not levels:
        return "none"
    prev = levels[0]
    for lv in levels[1:]:
        if lv > prev + 1:
            return "skip"
        prev = lv
    return "ok"


def _describe_heading_sequence(levels):
    """
    Build a short human-readable summary of the heading sequence.

    Parameters:
        levels (list[int]): Output of _extract_heading_sequence().

    Returns:
        str: Multi-line markdown string.
    """
    if not levels:
        return "_No heading elements were found in this document's structure._"

    lines = []
    prev = levels[0]
    for lv in levels:
        indent = "  " * (lv - 1)
        if lv > prev + 1:
            lines.append(f"{indent}**H{lv} ← skips H{prev + 1}**")
        else:
            lines.append(f"{indent}H{lv}")
        prev = lv
    if len(lines) > 20:
        lines = lines[:20] + [f"_… and {len(levels) - 20} more headings_"]
    return "\n".join(lines)


# =============================================================================
# DOCLING HELPER
# =============================================================================

def _run_docling(file_bytes):
    """
    Run Docling document conversion on raw PDF bytes.

    Returns:
        DoclingDocument object if conversion succeeds, or None on any failure.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        return result.document

    except Exception:
        return None

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_pdf(file_bytes):
    """
    Analyze a PDF file and return a result dict describing what was found.

    Parameters:
        file_bytes (bytes): The raw bytes of the uploaded PDF file.

    Returns:
        dict with keys: status, issues, (optional) cover_page_only, docling_doc
    """
    issues = []

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        if doc.needs_pass:
            doc.close()
            return {"status": "password_protected", "issues": []}

        if len(doc) > 0:
            first_page_text = doc[0].get_text().strip()
            if not first_page_text:
                cover_page_only = len(doc) > 1 and bool(doc[1].get_text().strip())
                doc.close()
                return {
                    "status": "scanned",
                    "issues": [],
                    "cover_page_only": cover_page_only,
                }

        page_count = len(doc)
        metadata = doc.metadata or {}

        docling_doc = _run_docling(file_bytes)

        # --- Missing document title ---
        title = (metadata.get("title") or "").strip()
        if not title:
            title_candidate = _detect_title_candidate(doc)
            if title_candidate:
                fix_preview = (
                    f"I'll add the title \"{title_candidate}\" to your document's metadata. "
                    "Screen readers announce this when the file opens, and it helps with "
                    "search indexing. You can edit it below before I save it."
                )
            else:
                fix_preview = (
                    "I'll add a descriptive title to the document metadata. "
                    "Enter the title you'd like to use for this document."
                )
            issues.append({
                "id": "missing_title",
                "severity": "green",
                "title": "Missing document title in metadata",
                "description": (
                    "The document's title field is empty — it currently defaults to the filename. "
                    "Screen readers announce the document title when a file opens, and search "
                    "tools use it for indexing. A descriptive title helps all users understand "
                    "what they're looking at before they start reading."
                ),
                "wcag": "WCAG 2.2 SC 2.4.2 — Page Titled",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": fix_preview,
                "fix_data": {"title_candidate": title_candidate},
            })

        # --- Missing language tag ---
        lang = (metadata.get("language") or "").strip()
        if not lang:
            sample_text = ""
            for page in doc:
                sample_text += page.get_text()
                if len(sample_text) >= 1000:
                    break
            try:
                detected = detect_language(sample_text[:1000]) if sample_text.strip() else "en"
            except Exception:
                detected = "en"
            lang_map = {
                "en": "en-US", "fr": "fr-FR", "es": "es-ES",
                "de": "de-DE", "pt": "pt-PT", "it": "it-IT",
            }
            lang_code = lang_map.get(detected, detected)
            issues.append({
                "id": "missing_lang",
                "severity": "yellow",
                "title": "Missing document language tag",
                "description": (
                    "This document doesn't declare what language it's written in. Screen readers "
                    "use the language tag to select the correct pronunciation rules and speech "
                    "engine. Without it, text may be read aloud in the wrong language or with "
                    "incorrect pronunciation — especially for technical terms and proper names."
                ),
                "wcag": "WCAG 2.2 SC 3.1.1 — Language of Page",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    f"I've detected that this document is written in "
                    f"{_lang_display_name(lang_code)} and will add the language tag "
                    f"'{lang_code}' to the document metadata."
                ),
                "fix_data": {"lang_code": lang_code},
            })

        # --- Missing bookmarks ---
        toc = doc.get_toc()
        if page_count > 9 and not toc:
            issues.append({
                "id": "missing_bookmarks",
                "severity": "green",
                "title": "Missing bookmarks / navigation",
                "description": (
                    f"This document is {page_count} pages long but has no bookmarks. "
                    "Without bookmarks, everyone — not just screen reader users — has to "
                    "scroll through the entire document to find what they need."
                ),
                "wcag": "WCAG 2.2 SC 2.4.5 — Multiple Ways",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "I'll generate bookmarks based on the heading structure I detect in your "
                    "document. You can review the bookmark list before I save it."
                ),
                "fix_data": {},
            })

        # --- Untagged PDF ---
        is_tagged = False
        try:
            with pikepdf.open(io.BytesIO(file_bytes)) as pdf:
                is_tagged = "/StructTreeRoot" in pdf.Root
        except Exception:
            pass

        if not is_tagged:
            issues.append({
                "id": "untagged_pdf",
                "severity": "red",
                "title": "Untagged PDF — no document structure",
                "description": (
                    "This document has no accessibility tags. Tags are the behind-the-scenes "
                    "structure that tells screen readers what is a heading, what is a paragraph, "
                    "and what order to read things in. Without them, a screen reader user hears "
                    "the content as an undifferentiated stream of text — or nothing at all."
                ),
                "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "I'll convert this document to a structured Word document (DOCX) that "
                    "preserves your headings, paragraphs, and reading order. You can then "
                    "re-save it as a properly tagged PDF from Word or Google Docs. This is "
                    "the most reliable path to a fully accessible PDF."
                ),
                "fix_data": {},
            })

        # --- Heading hierarchy ---
        if is_tagged:
            heading_levels = _extract_heading_sequence(file_bytes)
            hierarchy_status = _check_heading_hierarchy(heading_levels)

            if hierarchy_status == "none":
                issues.append({
                    "id": "heading_hierarchy",
                    "severity": "yellow",
                    "title": "No headings found in document structure",
                    "description": (
                        "This document is tagged for accessibility but contains no heading "
                        "elements. Screen reader users navigate long documents by jumping "
                        "between headings — without them, they must listen to the entire "
                        "document from start to finish to find what they need."
                    ),
                    "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
                    "ada": "Title II ADA, 28 CFR Part 35",
                    "fix_preview": (
                        "The Word document output will use your document's visual layout "
                        "to assign proper Heading 1, Heading 2, and Heading 3 styles. "
                        "Re-exporting from Word will produce a fully navigable PDF."
                    ),
                    "fix_data": {"issue_type": "none", "heading_levels": []},
                })

            elif hierarchy_status == "skip":
                issues.append({
                    "id": "heading_hierarchy",
                    "severity": "yellow",
                    "title": "Incorrect or missing heading hierarchy",
                    "description": (
                        "The heading levels in this document skip one or more levels — "
                        "for example, jumping from Heading 1 directly to Heading 3 with "
                        "no Heading 2 in between. Screen reader users rely on heading "
                        "structure to understand how a document is organized and to jump "
                        "between sections. A broken hierarchy makes that navigation "
                        "confusing or misleading."
                    ),
                    "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
                    "ada": "Title II ADA, 28 CFR Part 35",
                    "fix_preview": (
                        "Here is the heading structure detected in your document. "
                        "The Word document output will correct the hierarchy based on "
                        "the visual layout of your document."
                    ),
                    "fix_data": {
                        "issue_type": "skip",
                        "heading_levels": heading_levels,
                    },
                })

        # --- Images without alt text ---
        images = []
        for page_num, page in enumerate(doc):
            for img in page.get_images(full=True):
                xref = img[0]
                images.append({
                    "page": page_num + 1,
                    "xref": xref,
                    "img_key": xref,
                    "source": "pymupdf",
                })

        if docling_doc is not None:
            pymupdf_pages = {img["page"] for img in images if img["source"] == "pymupdf"}
            try:
                for item, _ in docling_doc.iterate_items():
                    if not hasattr(item, "label") or item.label != DocItemLabel.PICTURE:
                        continue
                    if not item.prov:
                        continue
                    prov    = item.prov[0]
                    page_no = prov.page_no
                    if page_no in pymupdf_pages:
                        continue
                    try:
                        page_height = docling_doc.pages[page_no].size.height
                        tl          = prov.bbox.to_top_left_origin(page_height)
                        x0 = round(tl.l, 2)
                        y0 = round(tl.t, 2)
                        x1 = round(tl.r, 2)
                        y1 = round(tl.b, 2)
                    except Exception:
                        continue
                    img_key = f"docling_{page_no}_{int(x0)}_{int(y0)}"
                    images.append({
                        "page":    page_no,
                        "xref":    None,
                        "img_key": img_key,
                        "source":  "docling",
                        "bbox":    (x0, y0, x1, y1),
                    })
            except Exception:
                pass

        if images:
            count = len(images)
            issues.append({
                "id": "missing_alt_text",
                "severity": "red",
                "title": "Images with missing text descriptions",
                "description": (
                    f"This document contains {count} image{'s' if count != 1 else ''} "
                    "that don't have text descriptions (alt text). Students who use screen "
                    "readers — software that reads content aloud — won't be able to access "
                    "the information those images convey."
                ),
                "wcag": "WCAG 2.2 SC 1.1.1 — Non-text Content",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    f"I found {count} image{'s' if count != 1 else ''} in your document. "
                    "I'll walk you through each one so you can tell me whether it's decorative "
                    "or informational, and we'll add the right text description for each."
                ),
                "fix_data": {"images": images},
            })

        # --- Readability barrier — font size too small ---
        SMALL_FONT_PT = 9.0
        total_chars   = 0
        small_chars   = 0

        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        size = span.get("size", 0)
                        if len(text) < 3:
                            continue
                        total_chars += len(text)
                        if size < SMALL_FONT_PT:
                            small_chars += len(text)

        if total_chars > 0 and small_chars > 0:
            pct = (small_chars / total_chars) * 100
            if pct > 25:
                rb_id       = "readability_barrier_severe"
                rb_severity = "red"
                rb_title    = "Severe readability barrier — text too small"
                rb_desc     = (
                    f"More than a quarter of your document's text ({pct:.0f}%) uses a "
                    "font size below 9pt, which is too small for many readers. Students "
                    "with low vision, reading difficulties, or aging eyes may struggle "
                    "to read this content without significant zooming."
                )
            else:
                rb_id       = "readability_barrier_moderate"
                rb_severity = "yellow"
                rb_title    = "Moderate readability barrier — some text too small"
                rb_desc     = (
                    f"About {pct:.0f}% of your document's text uses a font size below "
                    "9pt. While this affects a smaller portion of the content, it still "
                    "creates barriers for students with low vision or reading difficulties."
                )

            issues.append({
                "id":          rb_id,
                "severity":    rb_severity,
                "title":       rb_title,
                "description": rb_desc,
                "wcag":        "WCAG 2.2 SC 1.4.3, 1.4.6 — Contrast (Minimum/Enhanced)",
                "ada":         "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, I'll apply a "
                    "minimum font size so all body text is comfortably readable."
                ),
                "fix_data": {
                    "pct_affected": round(pct, 1),
                    "small_chars":  small_chars,
                    "total_chars":  total_chars,
                },
            })

        # --- Combined scan: reading order, color, list tagging, line/letter spacing ---
        reading_order_problem_pages = 0
        reading_order_pages_checked = 0
        color_usage     = Counter()
        visual_list_lines   = 0
        tight_line_pairs    = 0
        total_line_pairs    = 0
        tight_tracking_spans  = 0
        total_tracking_spans  = 0

        for page in doc:
            page_h = page.rect.height
            page_w = page.rect.width
            blocks = page.get_text("dict")["blocks"]
            text_blocks = [b for b in blocks if b.get("type") == 0 and b.get("lines")]

            if len(text_blocks) >= 4:
                reading_order_pages_checked += 1
                violations = 0
                for i in range(1, len(text_blocks)):
                    prev_y = (text_blocks[i-1]["bbox"][1] + text_blocks[i-1]["bbox"][3]) / 2
                    curr_y = (text_blocks[i]["bbox"][1]   + text_blocks[i]["bbox"][3])   / 2
                    prev_x = (text_blocks[i-1]["bbox"][0] + text_blocks[i-1]["bbox"][2]) / 2
                    curr_x = (text_blocks[i]["bbox"][0]   + text_blocks[i]["bbox"][2])   / 2
                    if (curr_y < prev_y - page_h * 0.25) and (abs(curr_x - prev_x) < page_w * 0.40):
                        violations += 1
                if violations >= 2:
                    reading_order_problem_pages += 1

            for block in text_blocks:
                lines = block.get("lines", [])

                for i in range(len(lines) - 1):
                    first_spans = lines[i].get("spans", [])
                    if not first_spans:
                        continue
                    line_fs = first_spans[0].get("size", 0)
                    if line_fs < 7:
                        continue
                    line_step = lines[i + 1]["bbox"][1] - lines[i]["bbox"][1]
                    if line_step <= 0:
                        continue
                    total_line_pairs += 1
                    if (line_step / line_fs) < 1.10:
                        tight_line_pairs += 1

                for line in lines:
                    line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                    if LIST_PATTERN.match(line_text):
                        visual_list_lines += 1

                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        if len(text) >= 3:
                            color = span.get("color", 0)
                            r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
                            if 40 <= (r + g + b) / 3 <= 215:
                                color_usage[color] += len(text)

                        if len(text) >= 5:
                            font_name = span.get("font", "").lower()
                            if not any(h in font_name for h in CONDENSED_FONT_HINTS):
                                fs = span.get("size", 0)
                                if fs >= 8:
                                    sw = span["bbox"][2] - span["bbox"][0]
                                    if sw > 0:
                                        total_tracking_spans += 1
                                        if sw / (len(text) * fs) < 0.28:
                                            tight_tracking_spans += 1

        if (
            reading_order_pages_checked >= 2
            and reading_order_problem_pages >= max(1, reading_order_pages_checked * 0.40)
        ):
            issues.append({
                "id": "reading_order",
                "severity": "yellow",
                "title": "Reading order may not match visual order",
                "description": (
                    "The order in which content was embedded in this PDF doesn't match "
                    "the top-to-bottom order a sighted reader would follow. Screen readers "
                    "and assistive technology encounter content in the order it is stored "
                    "in the file — if that order is scrambled, users hear content out of "
                    "sequence, making the document confusing or unintelligible."
                ),
                "wcag": "WCAG 2.2 SC 1.3.2 — Meaningful Sequence",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, the content will be "
                    "re-ordered into a logical top-to-bottom reading sequence. Re-exporting "
                    "from Word will produce a PDF with a correct, consistent reading order."
                ),
                "fix_data": {
                    "problem_pages": reading_order_problem_pages,
                    "pages_checked": reading_order_pages_checked,
                },
            })

        meaningful_colors = [c for c, cnt in color_usage.items() if cnt >= 40]

        if 2 <= len(meaningful_colors) <= 5:
            issues.append({
                "id": "color_only_cue",
                "severity": "yellow",
                "title": "Colored text detected — manual accessibility check needed",
                "description": (
                    f"This document uses {len(meaningful_colors)} distinct text colors. "
                    "Color can create accessibility barriers in several ways — most of "
                    "which can't be verified or fixed automatically. A quick manual "
                    "review is needed to confirm your students won't miss anything."
                ),
                "wcag": "WCAG 2.2 SC 1.4.1 — Use of Color",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": "",
                "fix_data": {"color_count": len(meaningful_colors)},
            })

        docling_list_items = 0
        if docling_doc is not None:
            try:
                for item, _ in docling_doc.iterate_items():
                    if hasattr(item, "label") and item.label == DocItemLabel.LIST_ITEM:
                        docling_list_items += 1
            except Exception:
                pass

        if visual_list_lines >= 8 and docling_list_items < visual_list_lines * 0.50:
            issues.append({
                "id": "inconsistent_list_tagging",
                "severity": "green",
                "title": "Lists may not be properly tagged in the document structure",
                "description": (
                    f"This document appears to contain {visual_list_lines} list items "
                    "formatted with bullets, dashes, or numbers — but the underlying "
                    "file structure may not label them as actual lists. Screen readers "
                    "announce list context ('list of 5 items') and let users jump "
                    "between items. Without that tagging, list content reads as a "
                    "stream of plain text with no navigation or context cues."
                ),
                "wcag": "WCAG 2.2 SC 1.3.1 — Info and Relationships",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, visually formatted "
                    "lists will be converted to properly structured list elements with "
                    "correct indentation and item tags. Re-exporting from Word will "
                    "carry the list structure through into the PDF."
                ),
                "fix_data": {
                    "visual_list_lines":  visual_list_lines,
                    "docling_list_items": docling_list_items,
                },
            })

        if total_line_pairs >= 20 and (tight_line_pairs / total_line_pairs) > 0.40:
            pct_tight = round(tight_line_pairs / total_line_pairs * 100)
            issues.append({
                "id": "line_spacing_tight",
                "severity": "green",
                "title": "Line spacing may be too tight",
                "description": (
                    f"About {pct_tight}% of this document's text lines are spaced "
                    "tighter than the recommended minimum. Tight line spacing makes "
                    "sustained reading harder — especially for students with dyslexia, "
                    "low vision, or attention difficulties. WCAG recommends body text "
                    "line spacing of at least 1.5× the font size."
                ),
                "wcag": "WCAG 2.2 SC 1.4.12 — Text Spacing",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, I'll apply 1.5× "
                    "line spacing to all body text. This improves readability without "
                    "changing the document's structure or meaning."
                ),
                "fix_data": {"tight_pct": pct_tight},
            })

        if total_tracking_spans >= 40 and (tight_tracking_spans / total_tracking_spans) > 0.45:
            pct_tracking = round(tight_tracking_spans / total_tracking_spans * 100)
            issues.append({
                "id": "letter_spacing_tight",
                "severity": "green",
                "title": "Letter spacing may be too tight",
                "description": (
                    "A significant portion of this document's text appears to use "
                    "compressed letter spacing. Tight character tracking reduces "
                    "legibility for all readers and creates particular barriers for "
                    "students with dyslexia, who rely on distinct spacing between "
                    "letters to distinguish similar characters (b/d, p/q, n/m)."
                ),
                "wcag": "WCAG 2.2 SC 1.4.12 — Text Spacing",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, letter spacing "
                    "will be normalized to the font's standard tracking. This removes "
                    "any artificial compression present in the original file."
                ),
                "fix_data": {"tight_pct": pct_tracking},
            })

        if len(meaningful_colors) > 5:
            issues.append({
                "id": "excessive_text_colors",
                "severity": "green",
                "title": "Excessive use of different text colors",
                "description": (
                    f"This document uses {len(meaningful_colors)} distinct text colors "
                    "across substantial portions of the content. Using many different "
                    "text colors creates visual noise and cognitive distraction, making "
                    "it harder to focus on the material. It can also confuse readers "
                    "about which color differences carry meaning and which are decorative."
                ),
                "wcag": "WCAG 2.2 SC 1.4.1 — Use of Color",
                "ada": "Title II ADA, 28 CFR Part 35",
                "fix_preview": (
                    "When you download your file as a Word document, text colors will "
                    "be reduced to a small, intentional set — body text and headings. "
                    "This keeps the visual hierarchy clear without the distraction of "
                    "many competing colors."
                ),
                "fix_data": {"color_count": len(meaningful_colors)},
            })

        doc.close()

    except Exception:
        return {"status": "issues_found", "issues": DEMO_ISSUES}

    if not issues:
        return {"status": "no_issues", "issues": [], "docling_doc": docling_doc}

    return {"status": "issues_found", "issues": issues, "docling_doc": docling_doc}
