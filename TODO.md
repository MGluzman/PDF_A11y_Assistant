# To Do Next — Agentic AI Accessibility Suite

**Last updated:** 2026-04-13

---

## PDF Assistant — Active Work

### 1. ⚡ Use Docling PICTURE detections for image alt text (not just PyMuPDF XObjects)
**Priority: high**

**Problem:** `analyze_pdf()` finds images using only PyMuPDF's `page.get_images()`, which
returns PDF image XObjects. In a pre-OCR'd scanned PDF, the page content is a text layer
over a background scan — any content images (photos, figures, diagrams) are pixel regions
within that background, not separate XObjects. PyMuPDF finds nothing (or just the background).
Docling's DocLayNet vision transformer analyses rendered pixels and DOES detect PICTURE regions
in these documents — but `analyze_pdf()` never looks at Docling's PICTURE detections. The alt
text workflow is entirely PyMuPDF-only and silently misses all embedded content images.

**Fix:**
1. In `analyze_pdf()`, after `_run_docling()`, walk `docling_doc.iterate_items()` for
   `DocItemLabel.PICTURE` items. Pull each item's page number and bounding box from
   `item.prov[0]`. Add to the images list alongside any XObjects PyMuPDF found.
   Store as `{"page": n, "bbox": (x0, y0, x1, y1), "source": "docling"}` to distinguish
   from XObject images which use `{"page": n, "xref": n, "source": "pymupdf"}`.

2. In the alt text workflow, branch on `source`:
   - `"pymupdf"` → existing path: `extract_image_from_pdf(pdf_bytes, xref)`
   - `"docling"` → new path: render the page with PyMuPDF at 300 DPI, crop at bbox using Pillow

3. Update `render_page_with_image_highlight()` to accept either an xref or a bbox so the
   red-border page-context view works for both image types.

4. Update `alt_text_results` keying — currently uses `xref` (int) as the dict key.
   For Docling images, use a string key like `"docling_{page}_{x0}_{y0}"` to avoid
   collisions.

5. Update `build_docx_from_pdf()` Docling path: when writing a PICTURE placeholder,
   look up the matching `alt_text_results` entry by page number and include the approved
   description alongside the placeholder.

---

### 3. Restructure the post-OCR screen ("happy with results?")
Currently `ocr_format_select` shows downloads first, then asks about continuing.
The decision should come first — downloading is never a gate to proceeding.

New structure:
1. Show quality score, "What we did" log, and text preview
2. Ask: "Are you happy with this result?"
   - **Yes, let's keep going** → proceed to issue list (no download required now)
   - **I want to download and review it first** → show download buttons, then ask
     continue or stop?
   - **No, I want to stop** → goodbye screen
3. Downloads are always available at the end via `render_choose_format()`

---

### 4. Save approved alt text descriptions into DOCX output
`build_docx_from_pdf()` now correctly excludes artifact/background images from
output. What's still missing: approved alt text descriptions for informational
images are collected in `st.session_state.alt_text_results` but never written
into the Word document as actual image alt text.

Fix: in `build_docx_from_pdf()` (PyMuPDF fallback path), when inserting an image
placeholder, look up the xref in `alt_text_results` and append the approved
description text alongside the placeholder. For the Docling path, do the same
by page number for non-excluded PICTURE items.

Longer term: use python-docx to insert actual inline images with `add_picture()`
and set the `descr` attribute on the drawing element for true Word alt text.

---

### 5. "No, let's try again" should offer an alternative approach
When faculty reject a proposed fix in `render_resolving_issue()`, the app currently
just returns to the issue list. Per CLAUDE.md it should either offer an alternative
fix path or ask the faculty member for more input before trying again.

What "alternative" means per issue:
- `missing_title` — let them type a completely different title
- `missing_lang` — show a language picker dropdown instead of auto-detected value
- `missing_bookmarks` — show the generated bookmark list for manual editing
- `untagged_pdf` / `heading_hierarchy` — explain why the fix works the way it does
  and ask if they want to proceed anyway or skip this issue

---

### 6. Missing issue detections in analyze_pdf()
These issues are defined in CLAUDE.md but not yet checked. All need to be added
to `analyze_pdf()`. Docling's structural data (available in `docling_doc`) should
be used where relevant — especially for reading order and list tagging.

| Issue | Severity | Notes |
|-------|----------|-------|
| Severe readability barriers (contrast/font/size, > 25% of doc) | 🔴 Red | Needs font color + background color extraction |
| Moderate readability barriers (same, < 25% of doc) | 🟡 Yellow | Same |
| Reading order doesn't match visual order | 🟡 Yellow | Docling reading order vs. PyMuPDF block order |
| Color used as only way to convey information | 🟡 Yellow | Hard without semantic understanding — flag for manual review |
| Inconsistent list tagging | 🟢 Green | Docling LIST_ITEM labels useful here |
| Line spacing too tight | 🟢 Green | PyMuPDF span metrics |
| Letter spacing too tight | 🟢 Green | PyMuPDF span metrics |
| Excessive text colors | 🟢 Green | Count distinct colors across spans |

---

### 7. Add upload processing time disclaimer
On the upload screen, add a brief notice below the file uploader letting
faculty know that analysis may take a few minutes — longer for large files.
Suggested wording:

> "Once you upload your file, it may take a few minutes to analyze depending
> on its size. Large files can take 5 minutes or more. Please be patient —
> the tool is working."

Place it as a `st.caption()` below the file uploader, visible only after
the copyright checkbox is checked (same condition that enables the uploader).

Priority: medium-low

---

### 7. Stale "Phase 1" comments in app.py
A few comments still reference "Phase 1" but the code is already real behavior.
Low priority — clean up when nearby code is touched rather than as a dedicated task.

---

## Notes from This Session (2026-04-13)
- Docling installed and integrated as primary PDF structure extractor
- `_run_docling()` runs at analysis time on digital PDFs; result cached in session state
- `build_docx_from_pdf()` uses Docling as primary path, PyMuPDF as fallback
- Image auto-classification added: `auto_classify_image()` + `run_auto_classification()`
  detect backgrounds, edge artifacts, and smudges via pixel stats + geometry
- Bulk review phase added: thumbnail grid of flagged images, one-click bulk removal
- Per-image screen now shows: full page with red highlight, extracted crop, zoom expander
- Three-option question_1: Decorative / Scan artifact / Informational
- Image-level nav added: Previous image, Skip this image, Skip fixing images
- Global Abandon button added to all remediation and human-in-the-loop screens
- Fixed trailing non-breaking space in _readable filenames (`.strip()` at upload)
- Fixed bulk_review first_idx bug (broken `or` condition matched classified images)
- Fixed Docling PICTURE exclusion: now uses `fully_excluded_pages` (page where every
  xref is removed) instead of per-page matching that dropped content images
- OCR pipeline verified end-to-end with real scanned PDF — all checklist items passed
