"""
test_docling.py
===============
Purpose: Evaluate Docling's capabilities on our test PDF to decide whether
         to integrate it into the PDF Remediation accessibility workflow.

We're testing four key questions:
  1. What structural elements can Docling detect? (headings, lists, tables, images)
  2. Can it determine reading order?
  3. Can it detect images and report on them (for alt text workflow)?
  4. How does its text extraction compare to what we get from PyMuPDF?

Run this from the PDF-Remediation directory:
  venv/Scripts/python test_docling.py
"""

import json
from pathlib import Path
from docling.document_converter import DocumentConverter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Path to the test PDF (one level up from PDF-Remediation/)
TEST_PDF = Path("../Test document with untagged image.pdf")

# ---------------------------------------------------------------------------
# Helper: print a section header so output is easy to scan
# ---------------------------------------------------------------------------

def header(title):
    """Prints a clearly visible section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def main():
    if not TEST_PDF.exists():
        print(f"ERROR: Test PDF not found at {TEST_PDF.resolve()}")
        return

    print(f"Testing Docling on: {TEST_PDF.resolve()}")
    print("Converting document — this may download ML models on first run...")

    # DocumentConverter is Docling's main entry point.
    # By default it uses its own layout model (no Tesseract needed for digital PDFs).
    converter = DocumentConverter()
    result = converter.convert(str(TEST_PDF))

    # The result has a .document property — a DoclingDocument object
    doc = result.document

    # ------------------------------------------------------------------
    # TEST 1: Raw exported text
    # Shows us the full extracted text in reading order
    # ------------------------------------------------------------------
    header("TEST 1: Full Text (reading order)")
    text = doc.export_to_text()
    # Print first 2000 chars so we don't flood the console
    print(text[:2000])
    if len(text) > 2000:
        print(f"\n... (truncated — full text is {len(text)} chars)")

    # ------------------------------------------------------------------
    # TEST 2: Structural elements breakdown
    # DoclingDocument has typed items: headings, paragraphs, tables, etc.
    # ------------------------------------------------------------------
    header("TEST 2: Structural Elements (by type)")

    # doc.texts gives us all text-based items with their label/type
    # Each item has: label (heading, paragraph, list_item, etc.), text, prov (page/location)
    element_counts = {}
    for item, _ in doc.iterate_items():
        label = str(item.label) if hasattr(item, 'label') else type(item).__name__
        element_counts[label] = element_counts.get(label, 0) + 1

    print("Element type counts:")
    for label, count in sorted(element_counts.items()):
        print(f"  {label:40s} {count}")

    # ------------------------------------------------------------------
    # TEST 3: Headings — hierarchy detection
    # Critical for accessibility: WCAG 2.1 SC 1.3.1 (Info and Relationships)
    # ------------------------------------------------------------------
    header("TEST 3: Headings (hierarchy)")

    # Import label type for filtering
    from docling_core.types.doc import DocItemLabel

    headings_found = 0
    for item, _ in doc.iterate_items():
        if hasattr(item, 'label') and item.label in (
            DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE
        ):
            # prov gives us page number and bounding box location
            page_num = item.prov[0].page_no if item.prov else "?"
            print(f"  [Page {page_num}] ({item.label}) {item.text[:80]}")
            headings_found += 1

    if headings_found == 0:
        print("  No headings detected.")

    # ------------------------------------------------------------------
    # TEST 4: Images — what does Docling know about them?
    # Critical for alt text workflow (WCAG 2.1 SC 1.1.1)
    # ------------------------------------------------------------------
    header("TEST 4: Images detected")

    images_found = 0
    for item, _ in doc.iterate_items():
        if hasattr(item, 'label') and item.label == DocItemLabel.PICTURE:
            page_num = item.prov[0].page_no if item.prov else "?"
            # Check if bounding box info is available
            bbox = item.prov[0].bbox if item.prov else None
            bbox_str = f"bbox={bbox}" if bbox else "no bbox"
            print(f"  [Page {page_num}] Image detected — {bbox_str}")
            # Check if there's any caption or alt text associated
            if hasattr(item, 'caption') and item.caption:
                print(f"    Caption: {item.caption}")
            images_found += 1

    if images_found == 0:
        print("  No images detected.")

    # ------------------------------------------------------------------
    # TEST 5: Tables
    # ------------------------------------------------------------------
    header("TEST 5: Tables detected")

    tables_found = 0
    for item, _ in doc.iterate_items():
        if hasattr(item, 'label') and item.label == DocItemLabel.TABLE:
            page_num = item.prov[0].page_no if item.prov else "?"
            print(f"  [Page {page_num}] Table detected")
            # Try to export table as markdown to see structure
            if hasattr(item, 'export_to_dataframe'):
                try:
                    df = item.export_to_dataframe()
                    print(f"    Shape: {df.shape[0]} rows x {df.shape[1]} cols")
                    print(f"    Preview:\n{df.head(3).to_string()}")
                except Exception as e:
                    print(f"    (Could not export to dataframe: {e})")
            tables_found += 1

    if tables_found == 0:
        print("  No tables detected.")

    # ------------------------------------------------------------------
    # TEST 6: Markdown export — shows structure + reading order together
    # This is one of Docling's showcase features
    # ------------------------------------------------------------------
    header("TEST 6: Markdown Export (structure + reading order)")

    md = doc.export_to_markdown()
    print(md[:3000])
    if len(md) > 3000:
        print(f"\n... (truncated — full markdown is {len(md)} chars)")

    # ------------------------------------------------------------------
    # TEST 7: JSON export — the full structured representation
    # Shows everything Docling knows about the document
    # ------------------------------------------------------------------
    header("TEST 7: JSON export (abbreviated)")

    doc_dict = doc.export_to_dict()

    # Just show the top-level keys and counts so we understand the schema
    print("Top-level keys:", list(doc_dict.keys()))

    # Count items in each section
    for key, val in doc_dict.items():
        if isinstance(val, list):
            print(f"  {key}: {len(val)} items")
        elif isinstance(val, dict):
            print(f"  {key}: dict with {len(val)} keys")
        else:
            print(f"  {key}: {repr(val)[:80]}")

    # ------------------------------------------------------------------
    # Summary: What can we use in our workflow?
    # ------------------------------------------------------------------
    header("SUMMARY")
    print(f"  Total text chars extracted : {len(text)}")
    print(f"  Structural element types   : {len(element_counts)}")
    print(f"  Headings found             : {headings_found}")
    print(f"  Images found               : {images_found}")
    print(f"  Tables found               : {tables_found}")
    print()
    print("Check the output above to decide:")
    print("  - Does reading order look correct? (TEST 1 / TEST 6)")
    print("  - Are headings correctly identified? (TEST 3)")
    print("  - Are images detected for alt text workflow? (TEST 4)")
    print("  - Is the element breakdown useful for issue detection? (TEST 2)")


if __name__ == "__main__":
    main()
