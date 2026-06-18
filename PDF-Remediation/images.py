"""Image extraction and classification."""

# -------------------------------------------------------------------------------
# images.py — image processing for the PDF Assistant
#
# Functions:
#   auto_classify_image()              — pixel/geometry heuristics to classify images
#   run_auto_classification()          — runs auto_classify_image on every image
#   render_page_with_image_highlight() — renders a PDF page with a red border around one image
#   extract_image_from_pdf()           — extracts a single image XObject by xref
#   extract_image_by_source()          — dispatches to the correct extractor by source type
# -------------------------------------------------------------------------------

import io

import fitz
from PIL import Image


def auto_classify_image(img_bytes, bbox, page_rect):
    """
    Automatically classify a PDF image as background, edge_artifact, artifact,
    or content using pixel statistics and geometry.

    Detection strategy:
      - Background: large coverage + low color variance (paper wash).
      - Edge artifact: thin strip near a page edge (scanner shadow or spine).
      - Artifact: small, very dark region anywhere on the page (smudge, speck).
      - Content: everything else — needs human review.

    Parameters:
        img_bytes (bytes): Raw extracted image bytes.
        bbox (fitz.Rect): Image bounding box in PDF point space.
        page_rect (fitz.Rect): Full page dimensions in PDF point space.

    Returns:
        dict with keys: classification, confidence, reason
    """
    import numpy as np

    try:
        img  = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        arr  = np.array(img, dtype=float)

        color_std       = float(arr.std(axis=(0, 1)).mean())
        mean_brightness = float(arr.mean())

        page_w   = page_rect.width  or 1
        page_h   = page_rect.height or 1
        img_w    = bbox.width       or 0
        img_h    = bbox.height      or 0
        coverage = (img_w * img_h) / (page_w * page_h)
        aspect   = (img_w / img_h) if img_h > 0 else 0

        margin      = 0.05
        near_left   = bbox.x0 < page_w * margin
        near_right  = bbox.x1 > page_w * (1 - margin)
        near_top    = bbox.y0 < page_h * margin
        near_bottom = bbox.y1 > page_h * (1 - margin)
        near_edge   = near_left or near_right or near_top or near_bottom

        if coverage > 0.40 and color_std < 30:
            confidence = min(0.95, 0.55 + (coverage - 0.40) + (30 - color_std) / 60)
            return {
                "classification": "background",
                "confidence": round(confidence, 2),
                "reason": (
                    f"Covers {coverage:.0%} of the page with very uniform colour "
                    f"(variation score {color_std:.1f}/255 — likely a paper background wash)."
                ),
            }

        thin = aspect > 8 or (aspect < 0.125 and aspect > 0)
        if near_edge and thin:
            return {
                "classification": "edge_artifact",
                "confidence": 0.85,
                "reason": (
                    f"Thin strip near the page edge "
                    f"(aspect ratio {max(aspect, 1/aspect if aspect else 1):.1f}:1) — "
                    "likely a scanner shadow or book-spine border."
                ),
            }

        if near_edge and mean_brightness < 60:
            return {
                "classification": "edge_artifact",
                "confidence": 0.80,
                "reason": (
                    f"Dark region (brightness {mean_brightness:.0f}/255) near the page edge — "
                    "likely a scan shadow or dark border."
                ),
            }

        if mean_brightness < 40 and coverage < 0.10:
            return {
                "classification": "artifact",
                "confidence": 0.70,
                "reason": (
                    f"Small ({coverage:.1%} of page), very dark image "
                    f"(brightness {mean_brightness:.0f}/255) — likely a scan smudge or mark."
                ),
            }

        return {
            "classification": "content",
            "confidence": 0.50,
            "reason": "No clear artifact pattern detected — please review manually.",
        }

    except Exception as exc:
        return {
            "classification": "content",
            "confidence": 0.50,
            "reason": f"Classification could not run ({exc}).",
        }


def run_auto_classification(images, pdf_bytes):
    """
    Run auto_classify_image() on every image in the list.

    Parameters:
        images    (list[dict]): Image metadata dicts from analyze_pdf().
        pdf_bytes (bytes): Current working copy of the PDF.

    Returns:
        dict: {img_key: classification_result}
    """
    results = {}
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for img_meta in images:
            img_key  = img_meta.get("img_key", img_meta.get("xref"))
            source   = img_meta.get("source", "pymupdf")
            page_idx = img_meta["page"] - 1
            try:
                page      = doc[page_idx]
                page_rect = page.rect

                if source == "docling":
                    raw_bbox      = img_meta.get("bbox")
                    fitz_bbox     = fitz.Rect(*raw_bbox) if raw_bbox else fitz.Rect(0, 0, 0, 0)
                    img_bytes_raw, _ = extract_image_by_source(pdf_bytes, img_meta)
                else:
                    xref          = img_meta["xref"]
                    rects         = page.get_image_rects(xref)
                    fitz_bbox     = rects[0] if rects else fitz.Rect(0, 0, 0, 0)
                    img_info      = doc.extract_image(xref)
                    img_bytes_raw = img_info["image"] if img_info else None

                if img_bytes_raw:
                    results[img_key] = auto_classify_image(img_bytes_raw, fitz_bbox, page_rect)
                else:
                    results[img_key] = {
                        "classification": "content",
                        "confidence": 0.50,
                        "reason": "Image data could not be extracted for classification.",
                    }
            except Exception:
                results[img_key] = {
                    "classification": "content",
                    "confidence": 0.50,
                    "reason": "Classification failed for this image.",
                }
        doc.close()
    except Exception:
        pass
    return results


def render_page_with_image_highlight(pdf_bytes, page_num, xref=None, bbox=None):
    """
    Render a full PDF page and draw a thick red border around a specific image.

    Parameters:
        pdf_bytes (bytes): The current working copy of the PDF.
        page_num  (int):   0-based page index.
        xref      (int):   XObject xref — used for PyMuPDF images.
        bbox      (tuple): (x0, y0, x1, y1) in PDF points — used for Docling images.

    Returns:
        bytes: PNG image bytes of the highlighted page, or None on failure.
    """
    try:
        from PIL import ImageDraw

        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_num]

        if bbox is not None:
            x0, y0, x1, y1 = bbox
            rects = [fitz.Rect(x0, y0, x1, y1)]
        elif xref is not None:
            rects = page.get_image_rects(xref)
        else:
            rects = []

        dpi   = 150
        scale = dpi / 72
        mat   = fitz.Matrix(scale, scale)
        pix   = page.get_pixmap(matrix=mat)
        doc.close()

        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        if rects:
            draw = ImageDraw.Draw(img)
            for rect in rects:
                x0 = int(rect.x0 * scale)
                y0 = int(rect.y0 * scale)
                x1 = int(rect.x1 * scale)
                y1 = int(rect.y1 * scale)
                for offset in range(4):
                    draw.rectangle(
                        [x0 - offset, y0 - offset, x1 + offset, y1 + offset],
                        outline=(220, 38, 38),
                    )

        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    except Exception:
        return None


def extract_image_from_pdf(pdf_bytes, xref):
    """
    Extract a single image from a PDF by its cross-reference number.

    Parameters:
        pdf_bytes (bytes): The current working copy of the PDF.
        xref (int): The xref number of the target image.

    Returns:
        (bytes, str): Raw image bytes and extension, or (None, None) on failure.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        img_info = doc.extract_image(xref)
        doc.close()
        if img_info:
            return img_info["image"], img_info["ext"]
    except Exception:
        pass
    return None, None


def extract_image_by_source(pdf_bytes, img_meta):
    """
    Extract image bytes for either a PyMuPDF XObject or Docling PICTURE region.

    Parameters:
        pdf_bytes (bytes): Current working copy of the PDF.
        img_meta  (dict):  Image metadata dict from analyze_pdf().

    Returns:
        (bytes, str): Image bytes and extension, or (None, None) on failure.
    """
    source = img_meta.get("source", "pymupdf")

    if source == "pymupdf":
        return extract_image_from_pdf(pdf_bytes, img_meta["xref"])

    # Docling path: render the page and crop at the stored bounding box.
    try:
        bbox    = img_meta.get("bbox")
        page_no = img_meta.get("page")   # 1-based
        if bbox is None or page_no is None:
            return None, None

        x0, y0, x1, y1 = bbox

        doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
        page  = doc[page_no - 1]
        dpi   = 300
        scale = dpi / 72
        mat   = fitz.Matrix(scale, scale)
        pix   = page.get_pixmap(matrix=mat)
        doc.close()

        img_full = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        left   = max(0,             int(x0 * scale))
        top    = max(0,             int(y0 * scale))
        right  = min(img_full.width,  int(x1 * scale))
        bottom = min(img_full.height, int(y1 * scale))

        if right <= left or bottom <= top:
            return None, None

        cropped = img_full.crop((left, top, right, bottom))
        out = io.BytesIO()
        cropped.save(out, format="PNG")
        return out.getvalue(), "png"

    except Exception:
        return None, None
