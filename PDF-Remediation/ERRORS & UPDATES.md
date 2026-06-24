# Errors & Updates Log

---

## Error 001 — PIL Image Resize Crash on Image Display

**Date discovered:** 2026-06-16
**Origin:** Anna Belenko's machine during setup and testing (`C:\Users\ABelenko\PDF_Ally_Assistant\PDF-Remediation\`)
**Status:** Documented — fix ready to apply

---

### What went wrong

The app crashed with a PIL traceback whenever the **bulk review screen** appeared during the image alt text workflow. The crash happened at the moment the app tried to display a thumbnail image in the 3-column grid.

The error trace ended here:

```
File "app.py", line 4449, in render_image_alt_text
    st.image(img_bytes, use_container_width=True)
...
File "PIL/Image.py", line 2437, in resize
    im = self.im.resize(size, resample, box)
```

---

### Why it happened

`extract_image_from_pdf()` returns images in their native embedded format — which can be **CMYK JPEG, JPEG2000, palette-mode (P), 1-bit binary (mode "1"), or grayscale-alpha (LA)**. Streamlit internally calls `PIL.Image.resize()` on every image before displaying it. Certain Pillow versions (especially mismatches between machines) raise errors when resizing non-standard color modes like CMYK.

This doesn't crash on every machine because Pillow's behavior for those modes changed across versions. Anna's machine had a different Pillow version than the development machine, exposing the bug.

The same risk exists at **7 total `st.image(img_bytes, ...)` call sites** in `app.py` (lines 4449, 4543, 4561, 4581, 4678, 4682, 6074).

---

### How to fix it

**Paste the following prompt into Claude to apply the fix:**

> In `PDF-Remediation/app.py`, add a helper function called `safe_image_bytes(img_bytes)` directly before the `extract_image_from_pdf` function (line 1092). The function should open the raw bytes with PIL, convert any non-RGB/RGBA image mode (such as CMYK, P, L, LA, or 1-bit) to RGB, re-encode as PNG, and return the new bytes. If conversion fails for any reason, it should return the original bytes unchanged. Then replace all 7 occurrences of `st.image(img_bytes, ...)` in the file with `st.image(safe_image_bytes(img_bytes), ...)` — keeping all other arguments (width, use_container_width) exactly as they are. Add a comment to the helper explaining that PyMuPDF returns images in native PDF color modes and PIL resize can fail on non-standard modes depending on Pillow version.

---

## Update 002 — OCR Performance: Slow Processing on Large Files

**Date discovered:** 2026-06-16
**Origin:** Anna Belenko's machine during testing (large magazine scan)
**Status:** Documented — fix ready to apply

---

### What was observed

- Tesseract OCR took ~28 minutes on a magazine-sized scanned PDF
- EasyOCR appeared to freeze indefinitely before eventually completing

---

### Why it's slow

Three compounding problems in the current code:

1. **Serial page processing.** `run_ocr()` (app.py line 462) and `run_easyocr()` (line 658) both process pages one at a time in a loop — no parallelism. Every page waits for the previous one to finish.

2. **Tesseract OSD runs as a subprocess on every single page** inside `preprocess_pages()` (line 779). For a 50-page document, that's 50 separate Tesseract binary launches just for orientation detection, before any text extraction begins.

3. **Pages are rendered at 300 DPI** (line 771). A magazine page at 300 DPI is roughly a 2,500 × 3,300 pixel image. Tesseract and EasyOCR both produce equivalent accuracy at 150 DPI — which is 4× less data per page to process and store in memory.

---

### Expected impact of each fix

| Fix | Expected speedup |
|---|---|
| Process pages in parallel (`ThreadPoolExecutor`) | 4–8× (scales with CPU cores) |
| Render at 150 DPI instead of 300 DPI | ~3–4× |
| Run OSD only on first 2 pages, apply result globally | Meaningful on long docs |
| Add per-page progress bar | No speed change, but prevents "frozen" perception |
| Warn user before starting OCR on large files (>15 pages) | Manages expectations |

Combining parallel processing + lower DPI should bring a 28-minute Tesseract run down to roughly 3–6 minutes on a typical faculty laptop. EasyOCR will improve by the same factors but will always be slower than Tesseract on CPU-only machines because it runs a neural network per page.

**Note:** EasyOCR without a GPU will remain slow on large files regardless of these fixes. For faculty with standard laptops, Tesseract is the practical choice for anything over ~20 pages.

---

### How to fix it

**Paste the following prompt into Claude to apply the fix:**

> In `PDF-Remediation/app.py`, make the following changes to speed up OCR on large files:
>
> 1. **Lower render DPI:** In `preprocess_pages()` (around line 771), change the render matrix from `300 / 72` to `150 / 72` and update the `scale` variable accordingly. Update the docstring to reflect 150 DPI.
>
> 2. **Parallelize Tesseract:** Rewrite `run_ocr()` (line 462) to use `concurrent.futures.ThreadPoolExecutor` with `max_workers` set to `min(4, os.cpu_count() or 1)`. Process each page in parallel using `executor.map`, preserving the original page order in the returned list.
>
> 3. **Parallelize EasyOCR:** Rewrite `run_easyocr()` (line 655) to create the `easyocr.Reader` once before the parallel section, then use `ThreadPoolExecutor` the same way to process pages in parallel. The reader is thread-safe for `readtext()` calls.
>
> 4. **Limit OSD to first 2 pages:** In `preprocess_pages()`, run `pytesseract.image_to_osd()` only on pages 0 and 1. Store the most common rotation found. Apply that rotation to all remaining pages without calling OSD again. If OSD fails on both sample pages, skip rotation for all pages.
>
> 5. **Add a large-file warning:** In `render_running_ocr()` (around line 3484), before the spinner starts, count the pages in the uploaded PDF. If the page count exceeds 15, display an `st.warning()` message estimating the time (roughly 30 seconds per page for Tesseract) and telling the user the app will show progress as it works.
>
> 6. **Add a per-page progress bar:** Inside `run_ocr()`, accept an optional `progress_callback` parameter. After each page completes, call it with `(current_page, total_pages)`. In `render_running_ocr()`, pass a callback that updates an `st.progress()` bar.
>
> Keep all existing docstrings and add comments explaining why each change was made.

---

## Update 003 — OCR Redesign: User Choice Between Fast Scan and Comprehensive Scan

**Date:** 2026-06-16
**Origin:** Design decision following Update 002 performance analysis
**Status:** Documented — planned feature, not yet implemented

---

### What we're changing and why

Update 002 fixes the speed problem for simple documents. But for complex layouts — magazines, newsletters, multi-column textbooks — faster Tesseract still produces garbled output because it doesn't understand page structure. The real fix for those documents is to use Docling's OCR pipeline, which analyzes the page layout before running text recognition, the same way Acrobat does.

Rather than always running one engine, we give faculty a choice upfront based on what their document looks like. Faculty know their own documents, so this is a natural decision for them to make — and it eliminates the current awkward fallback pattern where Tesseract runs first, produces poor output, and then EasyOCR is offered as a consolation.

Docling's layout models are already downloaded and cached on any machine that has used the app to analyze a readable PDF. No additional installation is required to enable this feature.

---

### The new screen

A new screen appears after the user confirms they want to convert their scanned document, replacing the current direct handoff to `render_running_ocr`. The user sees two options:

---

**Option A — Quick Scan**
*Best for: syllabi, typed reports, articles, and other documents that are mostly text in a single column.*

Uses Tesseract OCR with parallel page processing. Fast and accurate for straightforward layouts. Not recommended if your document has multiple columns, tables, or a lot of images mixed with text.

---

**Option B — Comprehensive Scan**
*Best for: magazines, newsletters, multi-column textbooks, or any document with a complex layout.*

Uses Docling's full document understanding pipeline, which analyzes the page structure before reading the text — the same approach used by professional tools like Adobe Acrobat. Preserves columns, tables, captions, and reading order in the output. Takes longer than the Quick Scan but produces significantly better results for complex documents.

---

### What changes in the code

| What changes | Details |
|---|---|
| New screen between scanned doc confirmation and OCR | Slots in as a new `step` value, e.g. `"ocr_mode_select"` |
| `render_running_ocr()` | Unchanged — handles Option A (Tesseract with Update 002 speed fixes) |
| New `render_running_docling_ocr()` function | Calls `_run_docling()` with `PipelineOptions(do_ocr=True)` |
| `_run_docling()` | Add `do_ocr=True` pipeline option when called from OCR path |
| `build_docx()` | Option B uses Docling's own DOCX exporter instead, which preserves structure |
| `render_running_easyocr()` and two-engine fallback | Removed — replaced by the upfront choice |
| `score_ocr_quality()` | Still used for Option A; Option B uses Docling's own confidence scores |

---

### How to implement it

**Paste the following prompt into Claude to apply the fix:**

> In `PDF-Remediation/app.py`, redesign the OCR path to give users an upfront choice between two scan modes. Here is exactly what to build:
>
> 1. **Add a new step `"ocr_mode_select"`** that appears after the user confirms they want to convert their scanned document (currently, confirmation goes directly to `"running_ocr"`). Add a `render_ocr_mode_select()` function that displays the following two buttons:
>    - **"Quick Scan"** — label it "Mostly text, simple layout" with the description: "Best for syllabi, typed reports, and single-column articles. Fast." On click, set `st.session_state.step = "running_ocr"`.
>    - **"Comprehensive Scan"** — label it "Multi-column, tables, or lots of images" with the description: "Best for magazines, newsletters, and textbooks. Takes longer but preserves layout." On click, set `st.session_state.step = "running_docling_ocr"`.
>
> 2. **Add a new `render_running_docling_ocr()` function** modeled on `render_running_ocr()`. Inside it: call `_run_docling()` with `do_ocr=True` passed via `PipelineOptions`. Export the result to DOCX using Docling's own exporter. Store the result in `st.session_state.docx_bytes` and `st.session_state.ocr_engine_used = "docling"`. On completion, set `step = "ocr_format_select"`. Show a progress spinner with the message "Analyzing page layout and reading text — this may take a few minutes for longer documents."
>
> 3. **Update `_run_docling()`** to accept an optional `do_ocr=False` boolean parameter. When `True`, initialize `DocumentConverter` with `PipelineOptions(do_ocr=True)`. When `False` (the default), behavior is unchanged from the current implementation.
>
> 4. **Remove `render_running_easyocr()`** and the EasyOCR upgrade offer from `render_ocr_format_select()`. EasyOCR is no longer offered as a fallback — the upfront choice replaces it.
>
> 5. **Register `render_ocr_mode_select` and `render_running_docling_ocr`** in the step-to-function dispatch table at the bottom of the file.
>
> 6. **Update `render_ocr_format_select()`** to display "Docling (comprehensive scan)" as the engine name when `ocr_engine_used == "docling"`.
>
> Keep all existing docstrings and add comments explaining why each change was made. Follow the CLAUDE.md comment style throughout.

---

## Update 004 — Bookmarks Check: False Positives Against Acrobat-Verified Documents

**Date discovered:** 2026-06-24
**Origin:** Testing with a PDF that passed Adobe Acrobat's accessibility checker
**Status:** Documented — fix ready to apply

---

### What was observed

A PDF that passed Adobe Acrobat's accessibility checker (Bookmarks and navigation items verified) was still flagged by the app for "Missing bookmarks / navigation."

---

### Why it happens

The app and Adobe Acrobat check for navigation using two different PDF mechanisms:

- **The app** calls PyMuPDF's `doc.get_toc()`, which reads the PDF's `/Outlines` object — the explicit bookmark tree visible in a PDF viewer's navigation panel. If that object is absent or empty, the app flags the issue.

- **Adobe Acrobat** considers a document navigable if it has heading tags in the **StructTreeRoot** (the tag tree). Tagged headings let screen reader users jump between sections even without an explicit bookmark list.

A document can have a fully tagged heading structure — satisfying Acrobat's check — without having an `/Outlines` bookmark tree. In that case the app produces a false positive.

This is not a WCAG version issue. The relevant success criterion (WCAG 2.4.5 — Multiple Ways) is identical in WCAG 2.1 and 2.2. The discrepancy is purely about how each tool operationalizes the same criterion.

---

### The fix

Change the bookmarks check from a single condition to an either-or:

> Flag "Missing bookmarks / navigation" only if the document has **neither** an `/Outlines` bookmark tree **nor** heading tags in the StructTreeRoot.

Either one gives users a navigation path and satisfies WCAG 2.4.5. Only the absence of both warrants flagging the issue.

**Implementation note:** `is_tagged` and `heading_levels` are already computed in `analyze_pdf()` — the bookmarks check just needs to run after those values are available, and use them in the condition.

---

### How to fix it

**Paste the following prompt into Claude to apply the fix:**

> In `PDF-Remediation/analysis.py`, update the bookmarks check in `analyze_pdf()` so it uses an either-or condition. Currently the check fires whenever `doc.get_toc()` returns an empty list and the page count exceeds 9. Change it so the issue is only flagged when the document has neither an `/Outlines` bookmark tree (empty `get_toc()`) nor heading tags in the StructTreeRoot. To do this: move the `is_tagged` pikepdf check and the `_extract_heading_sequence()` call to run before the bookmarks check, store the heading levels in a variable, and add a condition that skips the bookmarks flag when `is_tagged` is True and heading levels were found. Avoid calling `_extract_heading_sequence()` twice — reuse the result for the heading hierarchy check that currently follows it. Add a comment explaining the either-or rationale.

---

---
