# To Do Next — Agentic AI Accessibility Suite

**Last updated:** 2026-04-16

---

## PDF Assistant — Active Work

### ~~1. ⚡ Use Docling PICTURE detections for image alt text~~ ✅ Done 2026-04-16
All 5 sub-steps implemented:
- `analyze_pdf()` merges Docling PICTURE items with PyMuPDF XObjects; each image dict
  now carries `img_key`, `source`, and `bbox` (Docling) or `xref` (PyMuPDF).
- New `extract_image_by_source()` dispatches on source (XObject extract vs. page crop).
- `render_page_with_image_highlight()` accepts `xref=` or `bbox=` keyword.
- All `alt_text_results` keying now uses `img_key` throughout the alt text workflow.
- `build_docx_from_pdf()` uses `img_key`-based page grouping for exclusion/description lookup.

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

### ~~4. Save approved alt text descriptions into DOCX output~~ ✅ Done 2026-04-16
Longer-term follow-up: use python-docx `add_picture()` + set the `descr`
attribute on the drawing element for true Word alt text (currently descriptions
are written as visible placeholder text).

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

### ~~7. Add upload processing time disclaimer~~ ✅ Done 2026-04-16

---

### ~~7. Stale "Phase 1" comments in app.py~~ ✅ Done 2026-04-16

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
