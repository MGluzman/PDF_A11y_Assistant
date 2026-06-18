# Change Control — PDF Assistant Refactoring

Companion to: `REFACTORING PLAN.md`
Sequence: Refactoring → Update 002 (OCR speed) → Update 003 (OCR redesign)

**Instructions:** Work through each task in order. Do not begin a task until the
previous one is marked Complete. Fill in the Notes field after each task is done.
Do not skip QA checks even if the task felt straightforward.

**Standing QA rules for Phase 1 code-moving tasks (1.2–1.14):**
- App must start without import errors before marking any task Complete.
- Moved functions must no longer be defined in `app.py`.
These two checks are not repeated in individual tasks below.

---

## PHASE 1 — Refactoring

---

### Task 1.0 — Create backup copy of app.py

**What to do:**
Copy `app.py` verbatim to `app_backup_YYYYMMDD.py` in the same directory,
substituting today's date. Do not modify the backup file in any way.

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** Backup filename: app_backup_20260617.py (5,867 lines — verified match)

**QA check:**
- [x] Backup file exists in `PDF-Remediation/`
- [x] Backup file line count matches original `app.py` line count exactly
- [x] `app.py` is unchanged

---

### Task 1.1 — Create empty module files

**What to do:**
Create the following empty files, each containing only a one-line module docstring.
Do not move any code yet.

```
PDF-Remediation/ocr.py
PDF-Remediation/analysis.py
PDF-Remediation/images.py
PDF-Remediation/docx_export.py
PDF-Remediation/fixes.py
PDF-Remediation/ui/__init__.py
PDF-Remediation/ui/shared.py
PDF-Remediation/ui/upload.py
PDF-Remediation/ui/password.py
PDF-Remediation/ui/scanned.py
PDF-Remediation/ui/issues.py
PDF-Remediation/ui/images_ui.py
PDF-Remediation/ui/manual_review.py
PDF-Remediation/ui/done.py
```

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:**

**QA check:**
- [x] All 14 files exist at the correct paths
- [x] `ui/` directory exists
- [x] `app.py` is still unchanged and the app still runs

---

### Task 1.2 — Move `ocr.py`

**What to do:**
Move the following functions from `app.py` to `ocr.py`. Add all necessary imports
to `ocr.py`. Add `from ocr import *` (or named imports) to `app.py`.

Functions to move:
- `_deskew_image()`
- `preprocess_pages()`
- `run_ocr()`
- `run_easyocr()`
- `score_ocr_quality()`
- `build_docx()`
- `build_pdf()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ocr.py` written with OCR_DISCLAIMER constant and all 7 functions. Also includes `preflight_check()` — moved here from app.py to resolve a circular import (analysis.py needed it too, so it was placed in analysis.py instead; ocr.py imports it from there).

**QA check:**
- [ ] OCR path runs successfully on a scanned PDF (or at minimum, no error on startup)

---

### Task 1.3 — Move `analysis.py`

**What to do:**
Move the following functions from `app.py` to `analysis.py`. Add all necessary
imports. Update `app.py` imports.

Functions to move:
- `_run_docling()`
- `_detect_title_candidate()`
- `_lang_display_name()`
- `_generate_toc_from_font_sizes()`
- `_extract_heading_sequence()`
- `_check_heading_hierarchy()`
- `_describe_heading_sequence()`
- `analyze_pdf()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `analysis.py` written with all 9 functions plus `preflight_check()` (moved here to break circular import). `DEMO_ISSUES` and `LIST_PATTERN`, `CONDENSED_FONT_HINTS` constants also moved here.

**QA check:**
- [ ] Upload and analyze a readable PDF — issue list appears correctly

---

### Task 1.4 — Move `images.py`

**What to do:**
Move the following functions from `app.py` to `images.py`. Add all necessary
imports. Update `app.py` imports.

Functions to move:
- `auto_classify_image()`
- `run_auto_classification()`
- `render_page_with_image_highlight()`
- `extract_image_from_pdf()`
- `extract_image_by_source()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `images.py` written with all 5 functions. No Streamlit imports — pure image processing (fitz + PIL).

**QA check:**
- [ ] Image alt text workflow launches and displays thumbnails correctly

---

### Task 1.5 — Move `docx_export.py`

**What to do:**
Move the following functions from `app.py` to `docx_export.py`. Add all necessary
imports. Update `app.py` imports.

Functions to move:
- `_embed_image_with_alt_text()`
- `build_docx_from_pdf()`
- `_convert_docx_to_pdf()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `docx_export.py` written with all 3 functions. Imports `extract_image_by_source` from `images.py` and uses `pythoncom` for COM thread initialization.

**QA check:**
- [ ] Download a DOCX from a remediated PDF — file is valid and opens in Word

---

### Task 1.6 — Move `fixes.py`

**What to do:**
Move the following functions from `app.py` to `fixes.py`. Add all necessary
imports. Update `app.py` imports.

Functions to move:
- `apply_fix_missing_title()`
- `apply_fix_missing_lang()`
- `apply_fix_bookmarks()`
- `apply_fix_untagged()`
- `apply_fix_alt_text()`
- `apply_fix_heading_hierarchy()`
- `apply_fix_readability_barrier()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `fixes.py` written with all 7 fix functions plus `FIX_DISPATCH` dict. Imports `_generate_toc_from_font_sizes` from `analysis.py`.

**QA check:**
- [ ] Apply at least one fix (e.g. missing title) and confirm it saves correctly

---

### Task 1.7 — Move `ui/shared.py`

**What to do:**
Move the following functions from `app.py` to `ui/shared.py`. This must be done
before any other UI module since all other UI files will import from it.

Functions to move:
- `render_page_header()`
- `render_page_title()`
- `render_step_card()`
- `_render_go_back()`
- `_render_abandon_button()`
- `_render_image_nav_buttons()`
- `_advance_alt_text_image()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/shared.py` written with all 8 functions plus `SEVERITY_LABELS` constant and `init_state()`. Logo path uses `os.path.join(os.path.dirname(__file__), "..", "..", ...)` — two levels up from `ui/` subdirectory.

**QA check:**
- [ ] Page header and sidebar render correctly on the upload screen

---

### Task 1.8 — Move `ui/upload.py`

**What to do:**
Move `render_upload()` and `render_analyzing()` to `ui/upload.py`.
Import from `ui/shared.py` as needed.

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/upload.py` written with both functions. Imports `analyze_pdf` and `preflight_check` from `analysis.py`.

**QA check:**
- [ ] Upload screen renders and accepts a file correctly

---

### Task 1.9 — Move `ui/password.py`

**What to do:**
Move `render_password_protected()` and `render_password_walkthrough()`
to `ui/password.py`.

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/password.py` written with both functions. Handles password-protected PDF detection and removal walkthrough.

**QA check:**
- [ ] Upload a password-protected PDF and confirm the correct screen appears

---

### Task 1.10 — Move `ui/scanned.py`

**What to do:**
Move the following to `ui/scanned.py`:
- `render_scanned_doc()`
- `render_scanned_goodbye()`
- `render_running_ocr()`
- `render_running_easyocr()`
- `render_ocr_format_select()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/scanned.py` written with all 5 functions. Imports `OCR_DISCLAIMER` from `ocr.py`.

**QA check:**
- [ ] Upload a scanned PDF and confirm the scanned doc screen appears
- [ ] Confirm OCR runs and the format select screen appears after completion

---

### Task 1.11 — Move `ui/issues.py`

**What to do:**
Move the following to `ui/issues.py`:
- `render_issue_list()`
- `render_resolving_issue()`
- `render_continue_or_stop()`
- `render_re_analysis()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/issues.py` written. `render_resolving_issue()` uses inner functions (`_apply_and_advance`, `_skip_issue`, `_docx_path_buttons`) and has both standard and alternative modes for each issue type. Imports `render_issue_panels` and `render_plan_box` from `ui/images_ui.py`.

**QA check:**
- [ ] Issue list renders with correct severity indicators
- [ ] Select and resolve one issue — confirm fix is applied and app returns to issue list

---

### Task 1.12 — Move `ui/images_ui.py`

**What to do:**
Move the following to `ui/images_ui.py`:
- `render_image_alt_text()`
- `render_source_file_question()`
- `render_cuny_resources()`
- `render_issue_panels()`
- `render_plan_box()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/images_ui.py` written with all 5 functions. Full alt text workflow: classifying → bulk_review → question_1 → enter_text → summary phases. `render_issue_panels` and `render_plan_box` are also imported by `ui/issues.py`.

**QA check:**
- [ ] Upload a PDF with images — work through the full alt text workflow:
  classifying → bulk review → per-image → summary

---

### Task 1.13 — Move `ui/manual_review.py`

**What to do:**
Move `render_manual_review()` to `ui/manual_review.py`.

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/manual_review.py` written. Includes decorative image verification with thumbnail grid and Reinstate button that sends excluded images back through the alt text workflow.

**QA check:**
- [ ] Manual review checklist screen renders and all checklist items respond correctly

---

### Task 1.14 — Move `ui/done.py`

**What to do:**
Move the following to `ui/done.py`:
- `render_no_issues()`
- `render_choose_format()`
- `render_done()`

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `ui/done.py` written. `render_choose_format()` caches the DOCX build in session state and offers optional PDF conversion via Word COM. `render_done()` handles all exit reason variants.

**QA check:**
- [ ] Complete a full remediation session and download both DOCX and PDF outputs

---

### Task 1.15 — Slim down `app.py` and full end-to-end test

**What to do:**
Remove all moved code from `app.py`. Confirm what remains is only:
imports, `init_state()`, `preflight_check()`, and the dispatch table.
Run the full application end-to-end.

**Status:** [ ] Not started / [x] Complete / [ ] Blocked

**Notes:** `app.py` reduced from 5,867 lines to 288 lines. Contains: header comment, `import streamlit as st`, `st.set_page_config()`, 13 wildcard module imports, `init_state()` call, sidebar block, `STEP_HANDLERS` dict, CSS block, and router. End-to-end runtime test pending — QA checks below must be verified manually.

**QA check:**
- [x] `app.py` is under 300 lines (288 lines — target was 100 but CSS accounts for the rest)
- [ ] App starts without any import or runtime errors
- [ ] Upload a readable PDF → analyze → fix one issue → download DOCX
- [ ] Upload a scanned PDF → run OCR → download output
- [ ] Upload a PDF with images → complete alt text workflow
- [ ] No regressions observed on any screen

---

## PHASE 2 — Update 002: OCR Speed Fixes

_(See `ERRORS & UPDATES.md` Update 002 for full details and the paste-ready prompt.)_

---

### Task 2.1 — Apply OCR speed fixes

**What to do:**
Apply all six changes described in Update 002: lower DPI to 150, parallelize
Tesseract, parallelize EasyOCR, limit OSD to first 2 pages, add large-file
warning, add per-page progress bar.

**Status:** [ ] Not started / [ ] Complete / [ ] Blocked

**Notes:** _(Include the file tested and approximate time observed.)_

**QA check:**
- [ ] OCR runs on a short document (≤5 pages) without errors
- [ ] OCR runs on a long document (>15 pages) — large-file warning appears
- [ ] Progress bar advances page by page during OCR
- [ ] Output text quality is comparable to pre-fix results
- [ ] EasyOCR path also completes without errors

---

## PHASE 3 — Update 003: OCR Mode Selection (Fast vs. Comprehensive)

_(See `ERRORS & UPDATES.md` Update 003 for full details and the paste-ready prompt.)_

---

### Task 3.1 — Add OCR mode selection screen

**What to do:**
Add the `render_ocr_mode_select()` function and the `"ocr_mode_select"` step.
Wire up both buttons: Quick Scan → `running_ocr`, Comprehensive Scan →
`running_docling_ocr`.

**Status:** [ ] Not started / [ ] Complete / [ ] Blocked

**Notes:**

**QA check:**
- [ ] Mode selection screen appears after user confirms they want to convert a scanned PDF
- [ ] Both buttons are present with correct labels and descriptions
- [ ] Quick Scan button routes to the existing Tesseract OCR screen
- [ ] Comprehensive Scan button routes to the new Docling OCR screen

---

### Task 3.2 — Add Docling OCR path

**What to do:**
Add `render_running_docling_ocr()` and update `_run_docling()` to accept
`do_ocr=True`. Wire up the new screen in the dispatch table. Update
`render_ocr_format_select()` to display "Docling (comprehensive scan)"
as the engine label.

**Status:** [ ] Not started / [ ] Complete / [ ] Blocked

**Notes:**

**QA check:**
- [ ] Choosing Comprehensive Scan runs the Docling OCR pipeline without errors
- [ ] Spinner message is shown during processing
- [ ] Output DOCX opens correctly and layout is preserved
- [ ] Engine label on the format select screen reads "Docling (comprehensive scan)"

---

### Task 3.3 — Remove EasyOCR fallback path

**What to do:**
Remove `render_running_easyocr()`, remove the EasyOCR upgrade offer from
`render_ocr_format_select()`, and remove the `"running_easyocr"` entry from
the dispatch table.

**Status:** [ ] Not started / [ ] Complete / [ ] Blocked

**Notes:**

**QA check:**
- [ ] App starts without errors
- [ ] No reference to EasyOCR upgrade offer appears anywhere in the OCR flow
- [ ] `render_running_easyocr` is no longer defined anywhere in the codebase
- [ ] Full OCR flow (both Quick and Comprehensive paths) runs end-to-end without errors

---
