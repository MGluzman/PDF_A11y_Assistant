# Setup Guide — PDF Accessibility Remediation Tool

## What You Are Building
A Streamlit web application that helps faculty audit and fix PDF course materials
to comply with **WCAG 2.2 Level AA** and **Title II of the ADA**.

---

## Step 1 — Install Python

Python is the programming language this tool is written in.

1. Go to: **https://www.python.org/downloads/windows/**
2. Click **"Download Python 3.12.x"** (the big yellow button — latest 3.12 release)
3. Run the installer
4. **CRITICAL:** On the first screen, check **"Add python.exe to PATH"** before clicking Install
5. Click **"Install Now"**
6. When done, open **Command Prompt** and verify:
   ```
   python --version
   ```
   You should see something like: `Python 3.12.4`

---

## Step 2 — Install Tesseract OCR (required for scanned PDFs)

Tesseract is the OCR engine that reads text from scanned images.
The Python library (`pytesseract`) is just a wrapper — you need this binary too.

1. Go to: **https://github.com/UB-Mannheim/tesseract/wiki**
2. Download: **tesseract-ocr-w64-setup-5.x.x.exe** (the 64-bit Windows installer)
3. Run the installer — accept the defaults
4. Note the install path (default: `C:\Program Files\Tesseract-OCR\`)
5. You will enter this path in the app's Settings sidebar

---

## Step 3 — Set Up the Python Environment

1. Open **Command Prompt** (search "cmd" in Start menu)
2. Navigate to this folder:
   ```
   cd "C:\path\to\PDF_A11y_Assistant\PDF-Remediation"
   ```
3. Double-click **`setup.bat`** OR type in Command Prompt:
   ```
   setup.bat
   ```
4. Wait for all packages to download and install (~5–10 minutes on first run)

> **What is a virtual environment?**
> A virtual environment (`venv`) is an isolated copy of Python just for this
> project. It keeps packages separate from other Python projects, preventing
> version conflicts. Think of it like a dedicated toolbox for this app.

---

## Step 4 — Launch the App

Double-click **`launch.bat`** OR in Command Prompt:
```
launch.bat
```
Your browser will automatically open to: **http://localhost:8501**

---

## Library Reference

| Library | Purpose | Why It's Needed |
|---------|---------|----------------|
| `streamlit` | Web UI framework | Builds the entire browser interface |
| `PyMuPDF` (fitz) | PDF rendering | Converts pages to images, reads structure |
| `pdfplumber` | Text extraction | Extracts text with position/layout data |
| `pypdf` | PDF manipulation | Reads metadata, splits/merges PDFs |
| `pikepdf` | Low-level PDF editing | Reads/writes accessibility Tags tree |
| `reportlab` | PDF creation | Generates new, properly tagged PDFs |
| `pytesseract` | OCR wrapper | Calls Tesseract to read text from images |
| `pdf2image` | PDF→Image | Converts PDF pages to PIL images for OCR |
| `easyocr` | AI-based OCR | Alternative OCR, no separate binary needed |
| `Pillow` | Image processing | Standard Python image library |
| `opencv-python` | Advanced imaging | Deskewing, denoising scanned pages |
| `numpy` | Numerical arrays | Required by OpenCV and EasyOCR |
| `pdfminer.six` | Text/layout analysis | Fine-grained text extraction |
| `pandas` | Data tables | Builds audit reports and result tables |
| `langdetect` | Language detection | Detects document language for `/Lang` tag |
| `textstat` | Readability scoring | Flesch-Kincaid and other readability metrics |

---

## Accessibility Standards Reference

### WCAG 2.2 Level AA
Web Content Accessibility Guidelines version 2.1, conformance level AA.
This is the standard referenced in the DOJ's Title II regulations.
Key criteria for PDFs:
- **SC 1.1.1** Non-text Content — alt text for all images
- **SC 1.3.1** Info and Relationships — proper heading/list structure
- **SC 1.3.2** Meaningful Sequence — logical reading order
- **SC 1.4.3** Contrast (Minimum) — 4.5:1 ratio for normal text
- **SC 2.4.2** Page Titled — document must have a title
- **SC 3.1.1** Language of Page — language must be specified

### Title II of the ADA (28 CFR Part 35)
The DOJ updated Title II regulations in 2024 to require:
- State and local government entities must meet WCAG 2.2 AA for digital content
- Large entities (population ≥ 50,000): compliance by **April 24, 2026**
- Small entities: compliance by **April 26, 2027**
- Course content posted on websites or apps is covered

### PDF/UA-1 (ISO 14289-1)
The "Universal Accessibility" standard for PDFs.
Requires that all PDF content be tagged, have a document title,
specify a language, and be fully navigable by assistive technology.
