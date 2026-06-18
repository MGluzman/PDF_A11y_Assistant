"""Completion screens."""

# -------------------------------------------------------------------------------
# ui/done.py — no-issues, download format chooser, and session-end screens
#
# Functions:
#   render_no_issues()      — clean document congratulations + download option
#   render_choose_format()  — DOCX download + optional PDF conversion via Word
#   render_done()           — graceful session-end screen (various exit reasons)
# -------------------------------------------------------------------------------

import streamlit as st

from ui.shared import (
    render_page_header,
    render_page_title,
    _render_go_back,
    _render_abandon_button,
    init_state,
)
from docx_export import build_docx_from_pdf, _convert_docx_to_pdf


def render_no_issues():
    """
    Purpose: Tell the user the document looks good. Offer download or end session.
    Verbatim message from CLAUDE.md.
    """
    render_page_header()
    render_page_title("No issues found")
    st.divider()

    st.success(
        "🎉 Great news — your document looks good! We didn't find any accessibility "
        "issues that need attention. Your students should be able to access this content "
        "without barriers. Nice work!"
    )

    st.markdown("**What would you like to do?**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Download my file",
            type="primary",
            use_container_width=True,
        ):
            st.download_button(
                label="Download PDF",
                data=st.session_state.file_bytes,
                file_name=st.session_state.file_name,
                mime="application/pdf",
            )
    with col2:
        if st.button("I'm all set, thanks.", use_container_width=True):
            st.session_state.step = "done"
            st.session_state.done_reason = "clean_exit"
            st.rerun()

    _render_go_back("upload")


def render_choose_format():
    """
    Purpose: Deliver the remediated file to the faculty member.

    Two-step flow:
      1. Always show the fully remediated DOCX for immediate download.
      2. Offer to convert that DOCX to a properly tagged, accessible PDF
         using Microsoft Word via docx2pdf. The PDF carries all heading
         structure, image alt text, and accessibility fixes through —
         unlike a raw PDF export from pikepdf, which only has metadata.

    Per CLAUDE.md: file name gets "_edited" appended before the extension.
    """
    if st.session_state.get("untagged_pdf_pending"):
        if "untagged_pdf" not in st.session_state.resolved_ids:
            st.session_state.resolved_ids.append("untagged_pdf")
            st.session_state.resolved_count += 1
        st.session_state.untagged_pdf_pending = False

    render_page_header()
    render_page_title("Save your file")
    st.divider()

    resolved = len(st.session_state.resolved_ids)
    st.success(f"Great work — you've resolved {resolved} accessibility issue(s).")

    base_name = st.session_state.file_name.replace(".pdf", "").replace(".PDF", "")
    docx_name = f"{base_name}_edited.docx"
    pdf_name  = f"{base_name}_edited.pdf"

    output_pdf_bytes = st.session_state.working_pdf_bytes or st.session_state.file_bytes
    if not st.session_state.edited_docx_bytes:
        with st.spinner("Building your remediated Word document..."):
            st.session_state.edited_docx_bytes = build_docx_from_pdf(output_pdf_bytes)
    docx_bytes = st.session_state.edited_docx_bytes

    # -------------------------------------------------------------------------
    # STEP 1 — DOCX download (always available)
    # -------------------------------------------------------------------------
    if "untagged_pdf" in st.session_state.resolved_ids:
        st.warning(
            "⚠️ **Heading structure may need review.** Because this document had no "
            "accessibility tags, heading styles in the Word file were inferred from "
            "font sizes — they may not perfectly match the document's intended structure. "
            "Please review headings in Word before re-publishing."
        )

    st.markdown("### Download your remediated Word document")
    st.markdown(
        "Your document has been rebuilt with all accessibility fixes applied — "
        "correct heading structure, images with alt text, and improved readability. "
        "This Word file is ready to edit, share, or convert to PDF."
    )
    st.download_button(
        label=f"⬇ Download {docx_name}",
        data=docx_bytes,
        file_name=docx_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True,
        key="download_docx",
    )

    st.divider()

    # -------------------------------------------------------------------------
    # STEP 2 — Optional PDF conversion via docx2pdf (Word COM on Windows)
    # -------------------------------------------------------------------------
    st.markdown("### Convert to accessible PDF (optional)")

    if st.session_state.edited_pdf_bytes:
        st.success("Your accessible PDF is ready to download.")
        st.download_button(
            label=f"⬇ Download {pdf_name}",
            data=st.session_state.edited_pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf",
        )
    else:
        st.markdown(
            "We can convert your remediated Word document to a fully accessible PDF "
            "right now using Microsoft Word on this machine. The PDF will include all "
            "heading structure, image alt text, and accessibility fixes — ready to "
            "upload to Blackboard or share with students."
        )
        if st.button(
            "Convert and download as PDF",
            use_container_width=True,
            key="convert_to_pdf",
        ):
            with st.spinner(
                "Converting to PDF using Microsoft Word — this may take a moment..."
            ):
                try:
                    st.session_state.edited_pdf_bytes = _convert_docx_to_pdf(docx_bytes)
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "PDF conversion was not successful. This usually means Microsoft "
                        "Word is not available on this machine.\n\n"
                        "**To create the accessible PDF yourself:** open the Word document "
                        "you downloaded above, then use **File → Save As** (or **Export**) "
                        "and choose PDF. Word will carry all the accessibility fixes through "
                        "into the PDF automatically.\n\n"
                        f"Technical detail: {exc}"
                    )

    _render_abandon_button()


def render_done():
    """
    Purpose: Gracefully end the session.
    Shown when user chooses to walk away (password, scanned doc) or finishes.
    """
    render_page_header()
    render_page_title("All done")
    st.divider()

    reason = st.session_state.get("done_reason", "")

    if reason == "password_exit":
        st.info(
            "No problem — whenever you have an unlocked version of the file, "
            "come back and I'll help you check it for accessibility issues."
        )
    elif reason == "scanned_exit":
        st.info(
            "Understood. If you change your mind and would like to convert this file "
            "to readable text, just come back and upload it again."
        )
    elif reason == "ocr_exit":
        st.success("Your converted file is ready whenever you need it.")
        st.markdown(
            "Whenever you're ready to work through the accessibility issues, "
            "come back and upload your converted file — I'll pick up right where we left off."
        )
    elif reason == "clean_exit":
        st.success("Your document is in great shape — no action needed.")
    else:
        resolved = len(st.session_state.resolved_ids)
        st.success(
            f"You've resolved {resolved} accessibility issue(s) — "
            "good progress for your students!"
        )
        st.markdown(
            "Whenever you're ready to continue, come back and upload your file again. "
            "I'll pick up right where we left off."
        )

    st.divider()
    if st.button("Start a new session", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_state()
        st.rerun()
