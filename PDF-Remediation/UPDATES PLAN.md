# Updates Plan — PDF Assistant

---

## What We Are Updating and Why

Four targeted improvements based on bugs and design decisions documented in
ERRORS & UPDATES.md. No structural refactoring — each update touches a specific
module and is independent of the others.

| Update | Source | Files affected |
|--------|--------|----------------|
| 1 — Safe image conversion (RGB) | Error 001 | `images.py`, `ui/images_ui.py` |
| 2 — Bookmarks check fix | Update 004 | `analysis.py` |
| 3 — Large file warning | Update 002 | `ui/scanned.py` |
| 4 — OCR speed improvements | Update 002 | `ocr.py` |
| 5 — Fast vs. Comprehensive OCR | Update 003 | `ocr.py`, `ui/scanned.py`, `app.py` |

---

## Setup Step — Reduce Permission Prompts

Before beginning, run the `/fewer-permission-prompts` skill. This scans recent
transcripts and adds common read-only tool calls to the project allowlist so
implementation steps can run without interruption.

After setup, use the `/verify` skill after each update to confirm the app runs
correctly before moving to the next step.

---

## Update 1 — Safe Image Conversion (RGB)

**Source:** Error 001 in ERRORS & UPDATES.md
**Risk:** Low — isolated helper function, no logic change

### What changes

PyMuPDF returns images in their native PDF color modes: CMYK, JPEG2000,
palette-mode (P), 1-bit binary, or grayscale-alpha (LA). Streamlit calls
`PIL.Image.resize()` internally on every displayed image. Pillow raises an
error when resizing certain non-standard modes, and that behavior varies
across Pillow versions — causing the crash on Anna's machine.

The fix: a single helper that normalizes any image to RGB before display.

### Step 1 — Add `safe_image_bytes()` to `images.py`

Add the following function directly before `extract_image_from_pdf()` in
`images.py`:

```python
def safe_image_bytes(img_bytes):
    # PyMuPDF returns images in native PDF color modes (CMYK, P, LA, 1-bit).
    # PIL.Image.resize() raises on non-standard modes in some Pillow versions.
    # Convert to RGB before passing to Streamlit to prevent crashes.
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return img_bytes
```

### Step 2 — Replace all `st.image(img_bytes, ...)` calls

In `ui/images_ui.py`, replace every occurrence of `st.image(img_bytes, ...)`
with `st.image(safe_image_bytes(img_bytes), ...)`. Keep all other arguments
(width, use_container_width) exactly as they are. There are 7 call sites total.

Add `from images import safe_image_bytes` to the imports at the top of
`ui/images_ui.py`.

### Verify

Run `/verify` — upload a PDF with images and confirm the bulk review screen
and per-image screens display thumbnails without crashing.

---

## Update 2 — Bookmarks Check Fix

**Source:** Update 004 in ERRORS & UPDATES.md
**Risk:** Low — logic change to one condition in `analysis.py`

### What changes

The current check flags "Missing bookmarks" whenever `doc.get_toc()` returns
an empty list and the document is more than 9 pages. This produces false
positives against documents that passed Adobe Acrobat's accessibility checker,
because Acrobat accepts heading tags in the StructTreeRoot as sufficient
navigation — no explicit `/Outlines` bookmark tree required.

The fix: flag the issue only when the document has neither an `/Outlines`
tree nor heading tags in the StructTreeRoot.

### Step 1 — Reorder computations in `analyze_pdf()`

In `analysis.py`, move the `is_tagged` pikepdf check so it runs **before**
the bookmarks check (currently it runs after). The block currently at
approximately line 621 should be relocated above the bookmarks check at
approximately line 600.

### Step 2 — Call `_extract_heading_sequence()` once, reuse the result

Immediately after the `is_tagged` check, call `_extract_heading_sequence()`
and store the result:

```python
heading_levels = _extract_heading_sequence(file_bytes) if is_tagged else []
```

Remove the separate `_extract_heading_sequence()` call that currently appears
inside the heading hierarchy block (approximately line 652) and replace it
with the already-computed `heading_levels` variable.

### Step 3 — Update the bookmarks condition

Change the bookmarks check from:

```python
if page_count > 9 and not toc:
```

to:

```python
has_heading_nav = is_tagged and bool(heading_levels)
if page_count > 9 and not toc and not has_heading_nav:
```

Add a comment above the condition explaining the either-or rationale:
a document with tagged headings satisfies WCAG 2.4.5 even without an
explicit `/Outlines` bookmark tree.

### Verify

Run `/verify` — upload the PDF that previously triggered the false positive
and confirm the bookmarks issue no longer appears.

---

## Update 3 — Large File Warning

**Source:** Update 002 in ERRORS & UPDATES.md
**Risk:** Low — display-only addition, no processing logic changed

### What changes

Faculty uploading large scanned PDFs have no indication of how long OCR will
take. The app appears frozen. A warning before the process starts sets
expectations and prevents the user from thinking the app has crashed.

### Step 1 — Add warning to `render_scanned_doc()` in `ui/scanned.py`

In `render_scanned_doc()`, before the OCR confirmation buttons, add a page
count check. If the uploaded PDF has more than 15 pages, display an
`st.warning()` with an estimated time:

```
⚠️ This document is [N] pages long. OCR may take several minutes —
roughly 30 seconds per page for a Quick Scan on a typical laptop.
The app will show progress as it works.
```

Retrieve the page count from `st.session_state.file_bytes` using
`fitz.open(stream=...).page_count`.

### Verify

Run `/verify` — upload a scanned PDF with more than 15 pages and confirm
the warning appears on the scanned doc screen before the user makes a choice.

---

## Update 4 — OCR Speed Improvements (Tesseract)

**Source:** Update 002 in ERRORS & UPDATES.md
**Risk:** Medium — changes to processing logic in `ocr.py`; preserve existing
behavior exactly, only change performance characteristics

### What changes

Three compounding problems make Tesseract slow on large files:
1. Pages are processed serially — one at a time, no parallelism
2. Pages are rendered at 300 DPI (4× more data than needed)
3. OSD (orientation detection) runs as a subprocess on every page

### Step 1 — Lower render DPI in `preprocess_pages()`

In `ocr.py`, in `preprocess_pages()`, change the render matrix from
`300 / 72` to `150 / 72`. Update the `scale` variable and the docstring
to reflect 150 DPI. Add a comment: Tesseract produces equivalent accuracy
at 150 DPI while processing 4× less data per page.

### Step 2 — Limit OSD to first 2 pages

In `preprocess_pages()`, run `pytesseract.image_to_osd()` only on pages
0 and 1. Store the most common rotation found across those two pages. Apply
that rotation to all remaining pages without calling OSD again. If OSD fails
on both sample pages, skip rotation correction for all pages.

### Step 3 — Parallelize `run_ocr()`

Rewrite `run_ocr()` in `ocr.py` to use `concurrent.futures.ThreadPoolExecutor`
with `max_workers=min(4, os.cpu_count() or 1)`. Process each page in parallel
using `executor.map`. Preserve the original page order in the returned list —
`executor.map` maintains order automatically.

Add an optional `progress_callback` parameter. After each page completes,
call it with `(current_page, total_pages)` if provided.

### Step 4 — Add progress bar to `render_running_ocr()`

In `ui/scanned.py`, in `render_running_ocr()`, create an `st.progress(0)`
bar before calling `run_ocr()`. Pass a callback that calls
`progress_bar.progress(current / total)`. Replace or supplement the existing
spinner with the progress bar.

### Verify

Run `/verify` — upload a multi-page scanned PDF and confirm:
- The progress bar advances as pages complete
- The final OCR output is correct and in page order
- Processing is noticeably faster than before

---

## Update 5 — Fast vs. Comprehensive OCR Mode Selection

**Source:** Update 003 in ERRORS & UPDATES.md
**Risk:** Medium — new screen, new function, dispatch table change, removal
of EasyOCR path. Implement after Update 4 is verified.

### What changes

Instead of always running Tesseract and offering EasyOCR as a fallback,
faculty choose upfront based on their document type:

- **Fast Scan** — Tesseract with the Update 4 speed improvements.
  Best for simple layouts (syllabi, typed reports, articles).
- **Comprehensive Scan** — Docling with `do_ocr=True`.
  Best for complex layouts (multi-column, tables, images mixed with text).

EasyOCR is removed entirely — replaced by the upfront choice.

### Step 1 — Update `_run_docling()` in `analysis.py`

Add an optional `do_ocr=False` parameter. When `True`, initialize
`DocumentConverter` with `PipelineOptions(do_ocr=True)`. When `False`
(the default), behavior is unchanged. Update the docstring.

### Step 2 — Add `render_running_docling_ocr()` to `ui/scanned.py`

Model this function on `render_running_ocr()`. Inside it:
- Show a spinner: "Analyzing page layout and reading text — this may take
  a few minutes for longer documents."
- Call `_run_docling(file_bytes, do_ocr=True)` from `analysis.py`.
- Export the result to DOCX using Docling's own DOCX exporter.
- Store the result in `st.session_state.docx_bytes`.
- Set `st.session_state.ocr_engine_used = "docling"`.
- On completion, set `st.session_state.step = "ocr_format_select"`.

### Step 3 — Add `render_ocr_mode_select()` to `ui/scanned.py`

Add a new screen function with two buttons:

| Button label | Subtitle | On click |
|---|---|---|
| Quick Scan | Mostly text, simple layout — best for syllabi, typed reports, single-column articles. Fast. | `step = "running_ocr"` |
| Comprehensive Scan | Multi-column, tables, or lots of images — best for magazines and textbooks. Takes longer but preserves layout. | `step = "running_docling_ocr"` |

### Step 4 — Reroute scanned doc confirmation

In `render_scanned_doc()`, change the "Yes, make this document readable"
button so it sets `step = "ocr_mode_select"` instead of `step = "running_ocr"`.

### Step 5 — Remove EasyOCR path

- Remove `render_running_easyocr()` from `ui/scanned.py`
- Remove the EasyOCR upgrade offer from `render_ocr_format_select()`
- Remove `run_easyocr()` from `ocr.py` (or comment it out with a note
  if you prefer to preserve it for reference)

### Step 6 — Update `render_ocr_format_select()`

When `st.session_state.ocr_engine_used == "docling"`, display
"Docling (comprehensive scan)" as the engine name in the format
selection screen.

### Step 7 — Update dispatch table in `app.py`

Add the two new step names to the routing dispatch table:
- `"ocr_mode_select"` → `render_ocr_mode_select`
- `"running_docling_ocr"` → `render_running_docling_ocr`

Remove `"running_easyocr"` from the table.

### Verify

Run `/verify` — test both paths:
1. Upload a scanned PDF → choose Quick Scan → confirm Tesseract runs with
   progress bar → confirm output is correct
2. Upload a scanned PDF → choose Comprehensive Scan → confirm Docling runs
   with spinner → confirm output is correct
3. Confirm EasyOCR offer no longer appears anywhere in the app

---

## Summary of File Changes

| File | Updates |
|------|---------|
| `images.py` | Add `safe_image_bytes()` helper (Update 1) |
| `ui/images_ui.py` | Replace 7 `st.image()` calls (Update 1) |
| `analysis.py` | Reorder checks, reuse heading_levels, update bookmarks condition (Update 2); add `do_ocr` param to `_run_docling()` (Update 5) |
| `ui/scanned.py` | Add large file warning (Update 3); add progress bar (Update 4); add mode select screen and Docling OCR screen; remove EasyOCR (Update 5) |
| `ocr.py` | Lower DPI, limit OSD, parallelize `run_ocr()`, add progress callback (Update 4); remove `run_easyocr()` (Update 5) |
| `app.py` | Update dispatch table (Update 5) |
