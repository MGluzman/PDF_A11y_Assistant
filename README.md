# PDF Accessibility Assistant

A Streamlit app that helps faculty audit and remediate PDF course materials for
compliance with WCAG 2.2 Level AA and Title II of the ADA.

Built as part of the **[CUNY OLS Agentic AI Mentorship Program 2026](https://guides.cuny.edu/agentic-ai-mentoring/)**.

---

## What It Does

Faculty upload a PDF and the tool analyzes it for accessibility issues — missing
alt text, untagged structure, reading order problems, color contrast, and more.
It walks through each issue with plain-language explanations, applies fixes, and
asks for confirmation before saving. Output is a remediated DOCX or PDF.

Issues are organized into three severity tiers: Red (serious), Yellow (moderate),
and Green (minor).

---

## Philosophy

Built around a **human-in-the-loop** model. Every fix requires explicit faculty
confirmation — the app never modifies a document without approval at each step.

The tool requires **no AI** to function. All analysis and remediation runs on
open source libraries. AI assistance is an optional feature; the core tool works
entirely without it.

---

## How This Was Built

Developed using **Claude Code** through the
[CUNY OLS Agentic AI Mentorship Program 2026](https://guides.cuny.edu/agentic-ai-mentoring/).
Claude Code served as a collaborative coding partner for workflow logic, Python
development, and accessibility standards research. All product decisions and code
review remained with the developer.

---

## Getting Started

See [PDF-Remediation/SETUP.md](PDF-Remediation/SETUP.md) for full instructions.

```bash
cd PDF-Remediation
streamlit run app.py
```
Opens at `http://localhost:8501`

> **First run:** Docling downloads model weights (~200–400 MB) on first launch.
> One-time only.

---

## Technology Stack

| Library | Purpose |
|---------|---------|
| Streamlit | Web UI |
| PyMuPDF (fitz) | PDF rendering and structure extraction |
| Docling | Document structure analysis |
| Tesseract OCR | Text extraction from scanned pages |
| EasyOCR | Alternative OCR engine |
| pdfplumber | Text and layout extraction |
| pikepdf | Low-level PDF editing |
| python-docx | DOCX output |
| Pillow / OpenCV | Image processing |

**Note on Docling:** Docling is the library that does the heaviest analytical
work — it reads a PDF's internal structure to identify headings, lists, reading
order, and figure locations. Most of the accessibility detections in this tool
depend on what Docling finds. It is open source (MIT license) and developed by
IBM Research. On first launch it downloads its model weights (~200–400 MB);
subsequent runs use the cached models and start normally.

Full list: [PDF-Remediation/requirements.txt](PDF-Remediation/requirements.txt)

---

## License

[CC BY-NC-SA 4.0](LICENSE) — Mariya Gluzman, Brooklyn College, CUNY
