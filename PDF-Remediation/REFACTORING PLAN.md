# Refactoring Plan — PDF Assistant

---

## Why We Are Refactoring

`app.py` is currently 6,598 lines. All application logic — OCR engines, PDF analysis,
accessibility fix functions, UI screens, and session state — lives in a single file.
This makes coordinated changes risky, slows navigation, and prevents two people from
working on different parts simultaneously. The refactor splits the file into focused
modules before any new feature work begins.

---

## New Architecture

```
PDF-Remediation/
│
├── app.py                  ← Entry point only: imports, session state init, routing dispatch table
│
├── ocr.py                  ← Everything related to OCR processing
├── analysis.py             ← PDF accessibility analysis
├── images.py               ← Image extraction and auto-classification
├── docx_export.py          ← DOCX and PDF output building
├── fixes.py                ← All apply_fix_* functions
│
└── ui/
    ├── __init__.py         ← Empty, marks ui/ as a Python package
    ├── shared.py           ← Shared UI components (page header, title, step cards, abandon button)
    ├── upload.py           ← render_upload(), render_analyzing()
    ├── password.py         ← render_password_protected(), render_password_walkthrough()
    ├── scanned.py          ← render_scanned_doc(), render_scanned_goodbye(), render_running_ocr(),
    │                          render_running_easyocr(), render_ocr_format_select()
    ├── issues.py           ← render_issue_list(), render_resolving_issue(), render_continue_or_stop(),
    │                          render_re_analysis()
    ├── images_ui.py        ← render_image_alt_text() and all image workflow helpers
    ├── manual_review.py    ← render_manual_review()
    └── done.py             ← render_choose_format(), render_done(), render_no_issues()
```

---

## Module Descriptions

### `app.py` (entry point)
After refactoring, this file contains only: imports, the `init_state()` function,
the `preflight_check()` call, and the step-to-function dispatch table at the bottom.
Nothing else. Target size: under 100 lines.

### `ocr.py`
All OCR-related processing functions:
- `preprocess_pages()` — renders pages and corrects orientation/skew
- `run_ocr()` — Tesseract OCR execution
- `run_easyocr()` — EasyOCR execution
- `score_ocr_quality()` — evaluates OCR output quality
- `_deskew_image()` — OpenCV skew correction helper
- `build_docx()` — assembles OCR text into a DOCX file
- `build_pdf()` — assembles OCR text into a PDF file

### `analysis.py`
The PDF accessibility analysis pipeline:
- `analyze_pdf()` — the main 681-line analysis function
- `_run_docling()` — Docling document conversion
- `_detect_title_candidate()` — title metadata helper
- `_lang_display_name()` — language code formatting
- `_generate_toc_from_font_sizes()` — table of contents detection
- `_extract_heading_sequence()` — heading structure extraction
- `_check_heading_hierarchy()` — heading validation logic
- `_describe_heading_sequence()` — human-readable heading summary

### `images.py`
Image extraction and classification logic:
- `auto_classify_image()` — classifies a single image as background/artifact/content
- `run_auto_classification()` — runs classification across all images in a document
- `render_page_with_image_highlight()` — renders a page with a bounding box drawn around a target image
- `extract_image_from_pdf()` — extracts a single image by xref
- `extract_image_by_source()` — dispatches extraction by source type (pymupdf or docling)

### `docx_export.py`
DOCX output construction from a remediated PDF:
- `build_docx_from_pdf()` — the main 321-line DOCX builder
- `_embed_image_with_alt_text()` — inserts an image with alt text into a DOCX document
- `_convert_docx_to_pdf()` — drives LibreOffice or Word to export DOCX as PDF

### `fixes.py`
All accessibility fix functions that modify the working PDF:
- `apply_fix_missing_title()`
- `apply_fix_missing_lang()`
- `apply_fix_bookmarks()`
- `apply_fix_untagged()`
- `apply_fix_alt_text()`
- `apply_fix_heading_hierarchy()`
- `apply_fix_readability_barrier()`

### `ui/shared.py`
UI components used across multiple screens:
- `render_page_header()` — sidebar and top-of-page header
- `render_page_title()` — standardized page title display
- `render_step_card()` — numbered step indicator cards
- `_render_go_back()` — Go Back button
- `_render_abandon_button()` — Abandon button
- `_render_image_nav_buttons()` — Previous / Skip / Skip all buttons for image workflow
- `_advance_alt_text_image()` — advances the alt text image index

### `ui/scanned.py`
All screens in the scanned document path:
- `render_scanned_doc()` — scanned document detection screen
- `render_scanned_goodbye()` — exit screen for users who decline OCR
- `render_running_ocr()` — Tesseract OCR progress screen
- `render_running_easyocr()` — EasyOCR progress screen
- `render_ocr_format_select()` — OCR result preview and format selection

### `ui/issues.py`
The issue workflow screens:
- `render_issue_list()` — full issue list with severity indicators
- `render_resolving_issue()` — per-issue fix screen (658 lines — largest function in the codebase)
- `render_continue_or_stop()` — prompt after each resolved issue
- `render_re_analysis()` — re-analysis offer after every three fixes

### `ui/images_ui.py`
The complete alt text workflow:
- `render_image_alt_text()` — 563-line function covering all phases: classifying, bulk review,
  per-image question, description entry, and summary
- `render_source_file_question()` — asks whether the faculty member has the original source file
- `render_cuny_resources()` — displays CUNY accessibility resource links
- `render_issue_panels()` — shared layout helper for issue explanation panels
- `render_plan_box()` — renders the "Here's the plan" box

### `ui/manual_review.py`
- `render_manual_review()` — the manual review checklist screen (281 lines)

### `ui/done.py`
- `render_no_issues()` — clean document confirmation screen
- `render_choose_format()` — DOCX vs PDF output format selection
- `render_done()` — final download screen (253 lines)

---

## How the Refactoring Will Be Carried Out

The approach is purely mechanical — no logic changes, no bug fixes, no new features.
Each step moves existing code to its new home and updates imports. The app is tested
after every step so any breakage has a single known cause.

### Step 0 — Backup
Create `app_backup_[date].py` as a verbatim copy of the current `app.py` before
any changes are made.

### Step 1 — Create the module files (empty)
Create all new `.py` files with only a module-level docstring. No code yet.
Verify the file structure looks correct before proceeding.

### Step 2 — Move non-UI modules first
Move functions to `ocr.py`, `analysis.py`, `images.py`, `docx_export.py`, and
`fixes.py` in that order. After each module is complete, add its import to `app.py`
and confirm the app still runs.

### Step 3 — Create the `ui/` package
Create `ui/__init__.py` and move `ui/shared.py` first, since every other UI module
depends on it. Test before proceeding.

### Step 4 — Move UI screens one file at a time
Move screens to their new files in dependency order:
`upload.py` → `password.py` → `scanned.py` → `issues.py` → `images_ui.py`
→ `manual_review.py` → `done.py`. Test after each file.

### Step 5 — Slim down `app.py`
Remove all moved code from `app.py`. What remains should be only imports,
`init_state()`, `preflight_check()`, and the dispatch table. Verify line count
is under 100.

### Step 6 — Full application test
Run the app end-to-end: upload a readable PDF, upload a scanned PDF, work through
at least one issue fix, and download output. Confirm all screens render correctly.

---
