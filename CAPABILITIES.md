# PDF Accessibility Assistant — Current Capabilities

**Last updated:** 2026-04-27

---

## What This Tool Does

The PDF Accessibility Assistant helps faculty members find and fix accessibility
problems in their course materials. It checks a PDF against WCAG 2.2 Level AA
and Title II ADA requirements, guides the faculty member through each issue in
plain language, and delivers a remediated file ready to share with students.

---

## Core Workflow

1. Faculty uploads a PDF
2. The app analyzes it and flags accessibility problems by severity
3. Faculty works through each issue one at a time, confirming every fix before it's saved
4. The app delivers a corrected Word (.docx) or PDF file

---

## What It Currently Handles

### Scanned Documents
- Detects PDFs where text was scanned as an image (unreadable by screen readers)
- Runs OCR (Tesseract, with EasyOCR as an enhanced second pass) to extract readable text
- Scores output quality and shows a text preview before the faculty member commits
- Exports a readable version as Word or PDF with `_readable` appended to the filename

### Accessibility Issue Detection
The app automatically checks for 7 categories of accessibility problems:

| Issue | Severity | What it means |
|-------|----------|---------------|
| Text scanned as image | 🔴 Critical | Screen readers cannot read image-based text at all |
| No document structure / tagging | 🔴 Critical | Screen readers receive no headings, no reading order, no landmarks |
| Images missing text descriptions | 🔴 Critical | Students who cannot see the image get no information about it |
| Text too small to read comfortably | 🔴 Critical (>25%) / 🟡 Moderate (1–25%) | Font size below 9pt creates barriers for low-vision readers |
| Missing or broken heading structure | 🟡 Moderate | Screen reader users cannot navigate or understand the document's structure |
| Missing document language tag | 🟡 Moderate | Screen readers may read content in the wrong language or pronunciation |
| Missing navigation bookmarks | 🟢 Minor | Long documents without bookmarks require everyone to scroll to find content |

### Issue Fixes
Each detected issue has a guided fix workflow. Faculty confirm every change before it is saved — nothing is applied automatically without approval.

| Issue | How it's fixed |
|-------|---------------|
| Scanned text | OCR conversion → new readable file |
| Untagged PDF | Noted; document structure applied on Word export |
| Missing alt text | Per-image workflow: classify each image, write or approve a description |
| Font size too small | Noted; minimum font size enforced on Word export |
| Heading hierarchy | Noted; correct heading structure applied on Word export |
| Missing language tag | Language auto-detected; faculty can override via 17-language dropdown |
| Missing bookmarks | Bookmarks generated from heading structure; faculty previews list before applying |

### Image Alt Text Workflow
When a document has images without text descriptions, the app runs a dedicated workflow:
- Auto-classifies each image (background, scan artifact, or content)
- Offers bulk removal of high-confidence non-content images
- Walks faculty through each remaining image: is it decorative, an artifact, or informational?
- If informational: is it critical or supplementary to understanding?
- Faculty writes or edits the description; app saves it to the output file

### Output
- Exports as **Word (.docx)** — structured with heading styles, ready for further editing or re-export as a tagged PDF
- Exports as **PDF** — text-based, ready to share
- Filename format: `original_name_edited.docx` / `original_name_edited.pdf`

---

## What It Does Not Yet Do

The following are planned but not yet implemented:

- **Reading order verification** — detecting when content is stored out of visual sequence
- **Excessive text colors** — flagging documents that use too many different text colors
- **Inconsistent list tagging** — detecting visual lists that aren't marked up as lists
- **Line spacing** — detecting text that is too tightly spaced for comfortable reading
- **Manual review checklist** — a guided screen for issues that require human judgment (see below)

### Issues That Require Human Review
Some accessibility problems cannot be detected automatically. A future screen will
prompt faculty to check these manually:

| Issue | Severity | Why it needs a human |
|-------|----------|----------------------|
| Charts and graphs | 🔴 Critical | Alt text must describe the data and meaning, not just the visual |
| Embedded video or audio | 🔴 Critical | Captions and transcripts must be verified by a person |
| Math and equations | 🔴 Critical | Screen reader compatibility depends on how equations are encoded |
| Color as only cue for meaning | 🟡 Moderate | Requires understanding the document's intent |
| Non-descriptive link text ("click here") | 🟡 Moderate | Judgment call whether link text conveys enough context |
| Table structure correctness | 🟡 Moderate | Header cell semantics must be verified visually |
| Abbreviations spelled out on first use | 🟢 Minor | Requires reading comprehension, not pattern matching |
| Non-English passages | 🟢 Minor | Requires identifying language of specific text segments |

---

## Standards Referenced

- **WCAG 2.2 Level AA** — Web Content Accessibility Guidelines
- **Title II of the ADA** — 28 CFR Part 35 (applies to state and local government entities, including public universities)
