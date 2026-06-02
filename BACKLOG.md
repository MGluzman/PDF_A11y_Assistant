# Backlog — Agentic AI Accessibility Suite

A running list of future functionality and improvement ideas.
Add to it freely — nothing here is committed or scheduled.

---

## Future Tools

### DOC / DOCX Assistant
A dedicated remediation tool for Microsoft Word documents.
Help faculty make Word files accessible before they are exported to PDF —
fixing heading structure, alt text, reading order, and language tags
directly in the source file. This is the right fix for the "untagged PDF"
problem that the PDF Assistant currently defers back to Word.

### PPT / PPTX Assistant
A dedicated remediation tool for PowerPoint presentations.
Many course materials live permanently in slide format and are never
converted to PDF. This tool would address slide reading order, alt text
for images and charts, slide titles, and color contrast directly in PPTX.

### XLS / XLSX / CSV Assistant
A dedicated tool for spreadsheets.
Accessible spreadsheets require meaningful column headers, no merged cells
used for layout, logical reading order, and descriptions for any embedded
charts. Particularly relevant for data-heavy course materials.

---

## Improvements to Existing Tools

### PDF Assistant — Text/Background Contrast Check (WCAG SC 1.4.3)
Automated detection of text that fails the minimum 4.5:1 contrast ratio (3:1 for large text 18pt+).

**Next implementation — Fill path analysis (preferred):**
Extract filled rectangles drawn behind text spans using PyMuPDF's path/drawing data.
Compare the fill color against the span's text color using the WCAG relative luminance
formula. Faster than pixel sampling and sufficient for the most common case: colored
text boxes, highlighted backgrounds, and branded header/footer bands.
Limitation: misses image backgrounds and gradients.

**Wishlist — Pixel sampling:**
Render each page to an image and sample the background pixels directly behind each
text span's bounding box (inset slightly to avoid sampling the text itself).
More reliable across all background types including images and gradients, but slower.
Would replace fill path analysis as the detection method when performance allows.

**Fix path for both:** Flag failing spans by page, show faculty the contrast ratio
and the WCAG threshold, and direct them to correct colors in the DOCX export.

---

### PDF Assistant — "Bring Your Own Claude API" (optional LLM OCR upgrade)
After the free-tier OCR (Tesseract + EasyOCR fallback) runs, offer faculty
with their own Anthropic API key the option to re-process the scanned pages
using Claude's vision model for significantly higher accuracy.
- API key entered in the Settings sidebar (stored only in session, never saved)
- Triggered manually by the user after reviewing the free-tier preview
- Needs clear copy explaining that this requires a separate API account at
  console.anthropic.com — it is NOT the same as a Claude.ai subscription
- Target: build alongside the DOC/DOCX and PPT/PPTX Assistants

---
