# To Do Next — Agentic AI Accessibility Suite

**Last updated:** 2026-03-31 — 7:10 PM

---

## PDF Assistant — Active Work

### 1. Verify updated OCR scanning pipeline (Priority: do first)
The OCR flow was significantly reworked in the last session. Needs end-to-end
testing with a real scanned PDF before moving on to anything else.

Checklist:
- [ ] Preprocessing runs without error (orientation detection, skew correction)
- [ ] Tesseract first-pass completes and stores text in session state
- [ ] Quality score and badge (✅ / ⚠️ / ❌) display correctly in preview screen
- [ ] "What we did" processing log shows correct entries
- [ ] Preview expander auto-opens on Fair/Poor quality
- [ ] "Try the enhanced scanner" button appears on Fair/Poor results
- [ ] "Try the enhanced scanner" button is hidden in collapsed expander on Good results
- [ ] EasyOCR second-pass runs and produces updated preview + log
- [ ] Both DOCX and PDF downloads work after Tesseract pass
- [ ] Both DOCX and PDF downloads work after EasyOCR pass
- [ ] If preprocessing fails, OCR still runs on plain page renders (fallback)
- [ ] Error messages are specific and actionable (not just "Tesseract failed")

---

### 2. Add "happy with results?" decision screen after OCR (do this second)
After OCR completes and the preview is shown, ask the user:

> "Are you happy with this result?"

Three choices:
1. **Yes, let's keep going** — proceed directly to the accessibility issue list.
   No download needed. The converted file is already in session state and will
   be offered as a download at the very end of the session.
2. **I want to download and review it first** — show DOCX/PDF download buttons,
   then ask: continue to analysis or stop for now?
3. **No, I want to stop** — goodbye screen.

Key design note: downloading is NEVER a gate to continuing. Faculty who trust
the preview can skip straight to analysis. The download is always available at
the end of the session via the existing render_choose_format() screen.

Currently the ocr_format_select screen shows downloads first, then asks about
continuing. This needs to be restructured so the decision comes first.

---

### 3. Missing issue detections in analyze_pdf()
These issues are defined in CLAUDE.md but analyze_pdf() does not check for
them yet. All checks need to be added to the analyze_pdf() function.

| Issue | Severity | Status |
|-------|----------|--------|
| Severe readability barriers — contrast, font, or size problems affecting > 25% of doc | 🔴 Red | Not started |
| Moderate readability barriers — same issues affecting < 25% of doc | 🟡 Yellow | Not started |
| Reading order doesn't match visual order | 🟡 Yellow | Not started |
| Color used as the only way to convey information | 🟡 Yellow | Not started |
| Inconsistent list tagging | 🟢 Green | Not started |
| Line spacing too tight | 🟢 Green | Not started |
| Letter spacing too tight | 🟢 Green | Not started |
| Excessive text colors | 🟢 Green | Not started |

---

### 3. Alt text descriptions not saved to DOCX output
The per-image alt text workflow collects descriptions into
`st.session_state.alt_text_results` but `build_docx_from_pdf()` never reads
that dict — the descriptions are silently lost when the user downloads.
Fix: pass alt_text_results into build_docx_from_pdf() and apply them as
Word image alt text via python-docx.

---

### 4. "No, let's try again" doesn't offer an alternative fix
When faculty reject a proposed fix (render_resolving_issue, line ~2555),
the app just returns to the issue list. Per CLAUDE.md it should offer an
alternative approach or ask for more input before trying again.

---

### 5. Stale "Phase 1" comments
Lines ~2617 and ~2678 in app.py still say "Phase 1" but the code is
already real Phase 2 behavior. Low priority — clean up when nearby code
is touched.

---

## Notes from Last Session (2026-03-31)
- Virtual environment created at PDF-Remediation/venv/, all packages installed
- OCR fallback pipeline built: Tesseract → quality score → optional EasyOCR
- Page preprocessing added: auto-rotation (Tesseract OSD) + deskew (OpenCV)
- Quality badges changed to ✅/⚠️/❌ to avoid confusion with 🔴/🟡/🟢 severity scale
- "What we did" processing log added to OCR results screen
- Scan quality disclaimer added to scanned document screen
- Tesseract error handling split into preprocessing vs. OCR for clearer diagnostics
- BACKLOG.md created in main folder (future tools + API upgrade idea)
