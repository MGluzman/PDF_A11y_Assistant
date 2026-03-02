# CLAUDE.md — PDF Assistant
# Project Instructions for Claude Code

## About This Tool
This tool is called **PDF Assistant**. It helps faculty remediate digital course
content to make it accessible and compliant with WCAG 2.1 Level AA and Title II
of the ADA. The tool is built with Streamlit and Python.

---

## Core Behavior

### Workflow Order
1. User uploads a PDF file
2. If the file is scanned (image-based), run OCR first before any analysis
3. Analyze the file and generate a prioritized issues list
4. Present issues using the 3-tier severity system (see below)
5. Ask the user where they want to start (suggest red light issues first)
6. Guide the user through fixes with choices for how to resolve each issue
7. Ask the user how they want to receive the updated content (RTF or PDF)

### OCR Rule
If a PDF contains pages where text is scanned as an image (no selectable text),
always run OCR on those pages FIRST before running the accessibility scan.
After OCR, flag any contextual issues that OCR could not automatically fix
(e.g., reading order, misrecognized headings, missing structure).

---

## 3-Tier Severity System

### 🔴 Red Light — Serious
Issues that severely impact legibility for ALL users, not just screen reader users.
Faculty must be advised to fix these before sharing the file publicly or with students.

> [Specific red light issue types to be defined — placeholder for expansion]

Examples likely to fall here:
- Entire document is a scanned image with no selectable text (OCR needed)
- No document structure / completely untagged PDF
- Text contrast so low the content is unreadable
- Document is password-protected in a way that blocks assistive technology

### 🟡 Yellow Light — Moderate
Issues that moderately impact all users but primarily affect users who rely on
screen readers or other assistive technology.

> [Specific yellow light issue types to be defined — placeholder for expansion]

Examples likely to fall here:
- Missing alt text on images
- Incorrect or missing heading hierarchy
- Tables without headers or summary
- Reading order does not match visual order
- Missing document language tag (/Lang)

### 🟢 Green Light — Minor
Issues that, when fixed, will bring the document to full compliance but do not
seriously prevent users from reading or interacting with the content.

> [Specific green light issue types to be defined — placeholder for expansion]

Examples likely to fall here:
- Missing document title in metadata
- Missing bookmarks/navigation for long documents
- Minor color contrast issues on non-body text
- Inconsistent list tagging

---

## User Output Options
When remediation is complete, ask the user how they want to receive their
updated content. Offer exactly two choices:

1. **Rich Text Format (RTF)** — so the faculty member can open it in a word
   processor (Word, Google Docs) and edit it further before re-publishing
2. **Accessible PDF** — a properly tagged, readable PDF file ready to share

---

## Standards References
All issue descriptions and recommendations must cite:
- **WCAG 2.1 Level AA** — cite the specific Success Criterion (e.g., SC 1.1.1)
- **Title II of the ADA** (28 CFR Part 35) — reference where applicable

---

## Style & Communication
- Address the faculty member in plain, non-technical language
- Explain WHY each issue matters, not just what it is
- When offering fix options, explain the tradeoffs of each choice
- Never overwrite or delete the original uploaded file

---

## Incomplete — To Be Continued
The following sections are placeholders and will be filled in by the project owner:
- Exact list of red light issue types
- Exact list of yellow light issue types
- Exact list of green light issue types
- Any additional workflow rules or edge cases
