"""Scanned document screens."""

# -------------------------------------------------------------------------------
# ui/scanned.py — OCR detection, conversion, and format-selection screens
#
# Functions:
#   render_scanned_doc()       — Red Light warning and OCR/walk-away choice
#   render_scanned_goodbye()   — graceful exit when user declines OCR
#   render_running_ocr()       — Tesseract OCR pipeline with preflight and error handling
#   render_running_easyocr()   — EasyOCR second-pass pipeline
#   render_ocr_format_select() — quality review, download, continue/stop choice
# -------------------------------------------------------------------------------

import io
import tempfile

import fitz
import streamlit as st
from PIL import Image

from ocr import (
    run_ocr,
    run_easyocr,
    score_ocr_quality,
    build_docx,
    build_pdf,
    preprocess_pages,
    OCR_DISCLAIMER,
)
from analysis import analyze_pdf, preflight_check
from ui.shared import (
    SEVERITY_LABELS,
    render_page_header,
    render_page_title,
    _render_go_back,
    init_state,
)


def render_scanned_doc():
    """
    Purpose: Inform the user the document contains scanned (image-based) text
    and stop analysis until OCR is complete.

    This is a Red Light issue — the most serious category.
    Per WCAG 2.2 SC 1.4.1: the "ANALYSIS STOPPED" label uses text, not color alone.
    """
    render_page_header()
    render_page_title("Scanned document detected")
    st.divider()

    if st.session_state.cover_page_only:
        scope_note = (
            "At least one page of your PDF contains text that was scanned as an image."
        )
    else:
        scope_note = (
            "Your PDF contains text that was scanned as an image."
        )

    st.error(
        f"🔴 **ANALYSIS STOPPED — {SEVERITY_LABELS['red']} Issue**\n\n"
        f"{scope_note} This creates serious accessibility barriers for most users: "
        "screen readers cannot read image-based text, students cannot search or copy "
        "it, and it cannot be resized or translated. "
        "This document cannot be analyzed or improved until it is converted to a "
        "readable PDF.\n\n"
        "**Would you like me to convert it now?**"
    )

    st.caption(
        "WCAG 2.2 SC 1.4.5 — Images of Text | Title II ADA, 28 CFR Part 35"
    )

    st.caption(
        "💡 **Tip:** The conversion tool will automatically detect and correct "
        "page orientation and slight skew. For best results, make sure your scan "
        "has clear contrast between the text and background — very faint or "
        "washed-out scans may still produce inaccurate text regardless of the "
        "scanner used."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, make this document readable.",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.step = "running_ocr"
            st.rerun()
    with col2:
        if st.button(
            "No, leave it as it is.",
            use_container_width=True,
        ):
            st.session_state.step = "scanned_goodbye"
            st.rerun()

    _render_go_back("upload")


def render_scanned_goodbye():
    """
    Purpose: Close the session gracefully when the user chooses not to convert
    their scanned document.

    Two choices:
      - Upload another file — resets state and returns to the upload screen
      - No, I'm done for now — ends the session
    """
    render_page_header()
    render_page_title("No changes made")
    st.divider()

    st.info(
        "No problem — you can return any time to convert this document and work "
        "through its accessibility issues. If you have another PDF you'd like to "
        "check, you can upload it now."
    )

    st.markdown("**What would you like to do?**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Upload another file",
            type="primary",
            use_container_width=True,
        ):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_state()
            st.rerun()
    with col2:
        if st.button(
            "No, I'm done for now.",
            use_container_width=True,
        ):
            st.session_state.step = "done"
            st.session_state.done_reason = "scanned_exit"
            st.rerun()

    _render_go_back("scanned_doc")


def render_running_ocr():
    """
    Purpose: Run real Tesseract OCR on the uploaded PDF.

    Steps performed here (per CLAUDE.md OCR Process):
      1. Configure pytesseract with the Tesseract path from sidebar settings.
      2. Render each page as a 300 DPI image using PyMuPDF.
      3. Extract text from each image using Tesseract.
      4. Build DOCX and PDF output files (with disclaimer) and store as bytes
         in session state so the format selection screen can serve them directly.
      5. Transition to ocr_format_select, or show an error if Tesseract fails.
    """
    render_page_header()
    render_page_title("Converting your document")
    st.divider()

    tesseract_path = st.session_state.get(
        "tesseract_path",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )

    preflight = preflight_check(
        tesseract_path=tesseract_path,
        output_paths=[tempfile.gettempdir()],
    )
    if not preflight["ok"]:
        st.error(
            "🔴 **Setup issue — cannot start OCR.**\n\n"
            + "\n\n".join(preflight["errors"])
        )
        if st.button("← Go back", type="primary"):
            st.session_state.step = "scanned_doc"
            st.rerun()
        return

    preprocess_error = None
    ocr_error        = None

    with st.spinner(
        "Checking page orientation, correcting any skew, then converting to "
        "readable text — this may take a moment for longer documents..."
    ):
        try:
            pil_images, preprocessing_log = preprocess_pages(
                st.session_state.file_bytes, tesseract_path
            )
        except Exception as e:
            preprocess_error = str(e)
            try:
                doc = fitz.open(stream=st.session_state.file_bytes, filetype="pdf")
                pil_images = []
                for page_num in range(len(doc)):
                    pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                    pil_images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
                doc.close()
                preprocessing_log = [
                    f"✔ {len(pil_images)} page{'s' if len(pil_images) != 1 else ''} detected",
                    f"⚠️ Orientation/skew correction skipped — {preprocess_error}",
                ]
            except Exception:
                pil_images = []
                preprocessing_log = []

        if pil_images:
            try:
                pages_text = run_ocr(pil_images, tesseract_path)

                quality_score, quality_label = score_ocr_quality(pages_text)
                st.session_state.ocr_quality_score  = quality_score
                st.session_state.ocr_quality_label  = quality_label
                st.session_state.ocr_engine_used    = "tesseract"
                st.session_state.ocr_processing_log = preprocessing_log + [
                    "✔ OCR performed using Tesseract",
                    f"✔ Quality estimate: "
                    f"{'✅' if quality_label == 'Good' else '⚠️' if quality_label == 'Fair' else '❌'} "
                    f"{quality_label} ({quality_score}%)",
                ]
                st.session_state.ocr_pages_text = pages_text

                st.session_state.ocr_docx_bytes = None
                st.session_state.ocr_pdf_bytes  = None

                ocr_pdf_bytes = build_pdf(pages_text)
                analysis_result = analyze_pdf(ocr_pdf_bytes)
                st.session_state.ocr_issues = (
                    analysis_result["issues"]
                    if analysis_result["status"] == "issues_found"
                    else []
                )
                st.session_state.working_pdf_bytes = ocr_pdf_bytes

            except Exception as e:
                ocr_error = str(e)
        else:
            ocr_error = "Could not render pages from this PDF."

    if ocr_error:
        st.error(
            "🔴 **Conversion failed — Tesseract OCR could not run.**\n\n"
            "This usually means Tesseract is not installed, or the path in the "
            "sidebar settings is incorrect.\n\n"
            f"**Error details:** `{ocr_error}`\n\n"
            "Please check the Tesseract path in the ⚙️ Settings panel on the left, "
            "then try again."
        )
        if preprocess_error:
            st.warning(
                f"Note: page preprocessing also reported an issue: `{preprocess_error}`"
            )
        if st.button("← Go back", type="primary"):
            st.session_state.step = "scanned_doc"
            st.rerun()
    else:
        st.session_state.step = "ocr_format_select"
        st.rerun()


def render_running_easyocr():
    """
    Purpose: Run EasyOCR as a second-pass scanner on the original uploaded PDF.

    EasyOCR uses a neural-network text detector and recogniser that handles
    low-quality scans, unusual fonts, and skewed pages better than Tesseract.
    It is slower and requires model weights (~200 MB, downloaded on first run).
    """
    render_page_header()
    render_page_title("Converting your document")
    st.divider()

    tesseract_path = st.session_state.get(
        "tesseract_path",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )

    preflight = preflight_check(
        tesseract_path=tesseract_path,
        output_paths=[tempfile.gettempdir()],
    )
    if not preflight["ok"]:
        st.error(
            "🔴 **Setup issue — cannot start enhanced OCR.**\n\n"
            + "\n\n".join(preflight["errors"])
        )
        if st.button("← Go back", type="primary"):
            st.session_state.step = "ocr_format_select"
            st.rerun()
        return

    easyocr_error = None

    with st.spinner(
        "Running the enhanced scanner — this may take a minute or two for "
        "longer documents. Hang tight..."
    ):
        try:
            pil_images, preprocessing_log = preprocess_pages(
                st.session_state.file_bytes, tesseract_path
            )

            pages_text = run_easyocr(pil_images)

            quality_score, quality_label = score_ocr_quality(pages_text)

            processing_log = preprocessing_log + [
                "✔ OCR performed using EasyOCR (enhanced scanner)",
                f"✔ Quality estimate: "
                f"{'✅' if quality_label == 'Good' else '⚠️' if quality_label == 'Fair' else '❌'} "
                f"{quality_label} ({quality_score}%)",
            ]

            st.session_state.ocr_pages_text     = pages_text
            st.session_state.ocr_quality_score  = quality_score
            st.session_state.ocr_quality_label  = quality_label
            st.session_state.ocr_engine_used    = "easyocr"
            st.session_state.ocr_processing_log = processing_log

            st.session_state.ocr_docx_bytes = None
            st.session_state.ocr_pdf_bytes  = None

            ocr_pdf_bytes = build_pdf(pages_text)
            analysis_result = analyze_pdf(ocr_pdf_bytes)
            st.session_state.ocr_issues = (
                analysis_result["issues"]
                if analysis_result["status"] == "issues_found"
                else []
            )
            st.session_state.working_pdf_bytes = ocr_pdf_bytes

        except Exception as e:
            easyocr_error = str(e)

    if easyocr_error:
        st.error(
            "🔴 **Enhanced scan failed.**\n\n"
            f"**Error details:** {easyocr_error}\n\n"
            "You can still download the Tesseract version of your document."
        )
        if st.button("← Go back to previous result", type="primary"):
            st.session_state.ocr_engine_used = "tesseract"
            st.session_state.step = "ocr_format_select"
            st.rerun()
    else:
        st.session_state.step = "ocr_format_select"
        st.rerun()


def render_ocr_format_select():
    """
    Purpose: Show OCR quality results, ask whether the faculty member is happy,
    then either advance to accessibility analysis or offer a download to review.

    Flow per CLAUDE.md OCR Step 7:
      1. Show quality score, processing log, and text preview.
      2. Show what accessibility issues were found.
      3. Ask: "Are you happy with this result?" — three choices:
           a. Yes, let's keep going      → proceed to issue list (no download required)
           b. Download and review first  → show download buttons, then re-ask
           c. No, I want to stop         → done screen
    """
    render_page_header()
    render_page_title("Choose your output format")
    st.divider()

    pages_text = st.session_state.ocr_pages_text
    page_count = len(pages_text)

    if not st.session_state.ocr_docx_bytes:
        with st.spinner("Preparing your readable files..."):
            st.session_state.ocr_docx_bytes = build_docx(pages_text)
            st.session_state.ocr_pdf_bytes  = build_pdf(pages_text)

    st.success(
        f"Conversion complete — {page_count} page{'s' if page_count != 1 else ''} "
        "of readable text extracted successfully."
    )

    quality_score = st.session_state.get("ocr_quality_score")
    quality_label = st.session_state.get("ocr_quality_label", "Unknown")
    engine_used   = st.session_state.get("ocr_engine_used", "Tesseract")

    badge          = {"Good": "✅", "Fair": "⚠️", "Poor": "❌"}.get(quality_label, "⚪")
    engine_display = "Tesseract OCR" if engine_used == "tesseract" else "EasyOCR (enhanced)"

    st.markdown(
        f"**Text quality estimate:** {badge} {quality_label} "
        f"({quality_score}% word-like tokens) — scanned using {engine_display}"
    )

    if quality_label == "Good":
        st.caption("The extracted text looks reliable. Review the preview below to confirm.")
    elif quality_label == "Fair":
        st.caption(
            "The extraction looks partially readable but some words may be inaccurate. "
            "Review the preview — if you see significant errors, try the enhanced scanner."
        )
    else:
        st.caption(
            "The extraction quality looks low — the text may contain significant errors. "
            "Review the preview and consider trying the enhanced scanner for a better result."
        )

    processing_log = st.session_state.get("ocr_processing_log", [])
    if processing_log:
        with st.expander("📋 What we did", expanded=False):
            for entry in processing_log:
                st.markdown(entry)

    with st.expander(
        f"👁 Preview extracted text ({page_count} page{'s' if page_count != 1 else ''})",
        expanded=(quality_label in ("Fair", "Poor")),
    ):
        st.caption(
            "This is the text extracted from your scanned document. "
            "Review it for accuracy before deciding how to proceed."
        )
        for i, page_text in enumerate(pages_text):
            st.markdown(f"**Page {i + 1}**")
            st.text_area(
                label=f"page_{i + 1}",
                value=page_text.strip() if page_text.strip() else "(No text detected on this page)",
                height=200,
                disabled=True,
                label_visibility="collapsed",
                key=f"ocr_preview_page_{i}",
            )
            if i < len(pages_text) - 1:
                st.divider()

    if engine_used == "tesseract" and quality_label in ("Fair", "Poor"):
        st.info(
            "**Not happy with the result?** I can try again using a more powerful "
            "scanner (EasyOCR) that handles difficult scans better. It takes a "
            "little longer, but often produces more accurate text."
        )
        if st.button("Try the enhanced scanner", use_container_width=True, key="try_easyocr"):
            st.session_state.step = "running_easyocr"
            st.rerun()
    elif engine_used == "tesseract" and quality_label == "Good":
        with st.expander("Want to try the enhanced scanner anyway?", expanded=False):
            st.caption(
                "The quality estimate looks good, but automated scoring isn't perfect. "
                "If you spot errors in the preview, you can still try the enhanced scanner."
            )
            if st.button(
                "Try the enhanced scanner",
                use_container_width=True,
                key="try_easyocr_optional",
            ):
                st.session_state.step = "running_easyocr"
                st.rerun()

    st.divider()

    ocr_issues = st.session_state.get("ocr_issues", [])

    if ocr_issues:
        red_count    = sum(1 for i in ocr_issues if i["severity"] == "red")
        yellow_count = sum(1 for i in ocr_issues if i["severity"] == "yellow")
        green_count  = sum(1 for i in ocr_issues if i["severity"] == "green")

        summary_parts = []
        if red_count:
            summary_parts.append(f"**{red_count} 🔴 Red Light**")
        if yellow_count:
            summary_parts.append(f"**{yellow_count} 🟡 Yellow Light**")
        if green_count:
            summary_parts.append(f"**{green_count} 🟢 Green Light**")

        st.info(
            "Here are the issues we found in your converted document, grouped by "
            "severity: " + ", ".join(summary_parts) + ". "
            "If you'd like, I can help you work through most of them."
        )
    else:
        st.success(
            "🎉 Great news — your converted document looks good! No additional "
            "accessibility issues were found. Your students should be able to "
            "access this content without barriers."
        )

    if not st.session_state.get("ocr_download_mode", False):

        st.markdown("**Are you happy with this result?**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                "Yes, let's keep going.",
                type="primary",
                use_container_width=True,
                key="ocr_continue_direct",
            ):
                if ocr_issues:
                    st.session_state.issues = ocr_issues
                    st.session_state.step   = "issue_list"
                else:
                    st.session_state.step = "no_issues"
                st.rerun()

        with col2:
            if st.button(
                "I want to download and review it first.",
                use_container_width=True,
                key="ocr_download_first",
            ):
                st.session_state.ocr_download_mode = True
                st.rerun()

        with col3:
            if st.button(
                "No, I want to stop.",
                use_container_width=True,
                key="ocr_stop_direct",
            ):
                st.session_state.step        = "done"
                st.session_state.done_reason = "ocr_exit"
                st.rerun()

    else:
        st.markdown(
            "Your converted file is ready to download. Choose a format below — "
            "it will be saved with **_readable** added to your original file name."
        )

        base_name = st.session_state.file_name.replace(".pdf", "").replace(".PDF", "")
        docx_name = f"{base_name}_readable.docx"
        pdf_name  = f"{base_name}_readable.pdf"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Word processor document (DOCX)**")
            st.caption(
                "Opens in Microsoft Word, Google Docs, or any compatible application. "
                "Best if you need to edit the content further before re-publishing."
            )
            st.download_button(
                label=f"⬇ Download {docx_name}",
                data=st.session_state.ocr_docx_bytes,
                file_name=docx_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True,
            )
        with col2:
            st.markdown("**New PDF document**")
            st.caption(
                "A text-based PDF ready to share or upload directly. "
                "Best if you want a finished file."
            )
            st.download_button(
                label=f"⬇ Download {pdf_name}",
                data=st.session_state.ocr_pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

        st.caption(f'📄 Note added to your file: "{OCR_DISCLAIMER}"')
        st.divider()

        st.markdown("**Ready to keep going?**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, let's keep going.",
                type="primary",
                use_container_width=True,
                key="ocr_continue_after_download",
            ):
                st.session_state.ocr_download_mode = False
                if ocr_issues:
                    st.session_state.issues = ocr_issues
                    st.session_state.step   = "issue_list"
                else:
                    st.session_state.step = "no_issues"
                st.rerun()
        with col2:
            if st.button(
                "No, I'm done for now.",
                use_container_width=True,
                key="ocr_done_after_download",
            ):
                st.session_state.ocr_download_mode = False
                st.session_state.step              = "done"
                st.session_state.done_reason       = "ocr_exit"
                st.rerun()

    _render_go_back("scanned_doc")
