# To Do Next — Agentic AI Accessibility Suite

**Last updated:** 2026-05-11

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

### ~~3. Restructure the post-OCR screen ("happy with results?")~~ ✅ Done 2026-04-27
Decision now comes before downloads. `render_ocr_format_select()` shows quality
score → processing log → text preview → issue summary, then a 3-way choice:
- **Yes, let's keep going** → straight to issue list, no download required
- **I want to download and review it first** → shows downloads + disclaimer,
  then asks continue or stop (`ocr_download_mode` flag controls this sub-path)
- **No, I want to stop** → done screen
Downloads still available at the end via `render_choose_format()`.

---

### ~~4. Save approved alt text descriptions into DOCX output~~ ✅ Done 2026-04-16
Longer-term follow-up: use python-docx `add_picture()` + set the `descr`
attribute on the drawing element for true Word alt text (currently descriptions
are written as visible placeholder text).

---

### ~~5. "No, let's try again" should offer an alternative approach~~ ✅ Done 2026-04-27
`render_resolving_issue()` now has a full alternative mode (`showing_alternative`
flag). Per-issue paths:
- `missing_title` → empty text input, type a title from scratch
- `missing_lang` → 17-language selectbox dropdown
- `missing_bookmarks` → live preview of generated bookmarks from document headings;
  apply button disabled if no headings detected
- `untagged_pdf` → explains the DOCX conversion path, "Got it — apply it anyway"
- `heading_hierarchy` → explains the font-size heuristic, "Got it — apply it anyway"
- fallback → generic "apply anyway" for any future issue types
Every alternative also has "Skip this issue for now" which adds to `skipped_ids`
and removes the issue from the active list. Progress caption shows skipped count.

---

### 6. Missing issue detections in analyze_pdf()
These issues are defined in CLAUDE.md but not yet checked. All need to be added
to `analyze_pdf()`. Docling's structural data (available in `docling_doc`) should
be used where relevant — especially for reading order and list tagging.

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| ~~Severe readability barriers (font size < 9pt, > 25% of doc)~~ | 🔴 Red | ✅ Done 2026-04-27 | `readability_barrier_severe` — detected via span size, fix in DOCX path |
| ~~Moderate readability barriers (font size < 9pt, 1–25% of doc)~~ | 🟡 Yellow | ✅ Done 2026-04-27 | `readability_barrier_moderate` — same detection, threshold-gated |
| Reading order doesn't match visual order | 🟡 Yellow | ⬜ Todo | Compare stored block order vs. visual top-to-bottom order |
| Color used as only way to convey information | 🟡 Yellow | ⬜ Todo | Hard without semantic understanding — flag for manual review |
| Inconsistent list tagging | 🟢 Green | ⬜ Todo | Docling LIST_ITEM labels useful here |
| Line spacing too tight | 🟢 Green | ⬜ Todo | PyMuPDF span metrics |
| Letter spacing too tight | 🟢 Green | ⬜ Todo | PyMuPDF doesn't expose reliably — rough heuristic at best |
| Excessive text colors | 🟢 Green | ⬜ Todo | Count distinct colors across spans |

---

### ~~8. Manual Review Checklist screen~~ ✅ Done 2026-05-11
Some accessibility issues cannot be detected algorithmically — they require a
human eye to evaluate. These are real WCAG 2.1 / Title II problems that the app
should surface, even if it can't fix them automatically.

**What to build:** A new workflow screen shown after all auto-detected issues are
resolved (or when the user says "I'm done"), positioned before the download screen.
Presents a structured checklist of manually-verifiable items with:
- Plain-language explanation of what to look for and why it matters
- "Looks fine" / "Needs attention" choice for each item
- Items marked "Needs attention" provide specific guidance on how to address them
- User can skip the whole screen if they choose

**Issues to include:**

| Issue | Severity | What to check |
|-------|----------|---------------|
| Charts, graphs, and diagrams | 🔴 Critical | Does the alt text describe the *data and meaning*, not just the visual appearance? A bar chart description should say what the bars represent and what the key takeaway is. |
| Embedded video or audio | 🔴 Critical | Is there a transcript or caption file? Can a student who can't hear the audio still access the content? |
| Math and equations | 🔴 Critical | Are equations image-based (unreadable) or text-based? Even text-based math notation (x², ∑) may not read correctly in all screen readers. |
| Color as only cue for meaning | 🟡 Moderate | Is color used to signal something (required fields, categories, warnings) without any other indicator — label, symbol, or text? |
| Non-descriptive link text | 🟡 Moderate | Do any links say "click here," "this link," or "read more" without context? Screen readers read link text in isolation. |
| Table structure correctness | 🟡 Moderate | Are header cells actually marked as headers, or just visually bold? Does the table read logically row by row without visual layout as a cue? |
| Abbreviations on first use | 🟢 Lower priority | Are acronyms and discipline-specific abbreviations spelled out the first time they appear? (e.g., "CUNY — City University of New York") |
| Non-English passages | 🟢 Lower priority | Does the document include quotes or passages in another language? Those sections should have their own language tag so screen readers switch pronunciation rules. |
| Decorative image verification | 🟢 Lower priority | Review any images the app auto-classified as decorative or removed as artifacts — confirm no content image was accidentally excluded. |

---

### ~~7. Add upload processing time disclaimer~~ ✅ Done 2026-04-16

---

### ~~7. Stale "Phase 1" comments in app.py~~ ✅ Done 2026-04-16

---

## Notes from This Session (2026-04-27)
- TODO #3: Post-OCR screen restructured — decision now comes before downloads;
  3-way satisfaction question; `ocr_download_mode` flag controls download sub-path
- TODO #5: "No, let's try again" now has per-issue alternative paths;
  `showing_alternative` flag; `skipped_ids` list; progress caption shows skipped count
- TODO #6 (partial): Font size readability detection added to `analyze_pdf()`;
  `readability_barrier_severe` (🔴 > 25%) and `readability_barrier_moderate` (🟡 1–25%);
  `apply_fix_readability_barrier()` registered in FIX_DISPATCH; alternative mode branch added
- Brooklyn College local server authorization pending; ngrok being explored for interim testing
- Repo: https://github.com/MGluzman/Agentic-AI

## Notes from Session (2026-04-13)
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
