"""Upload and analyzing screens."""

# -------------------------------------------------------------------------------
# ui/upload.py — landing/upload screen and the analysis spinner screen
#
# Functions:
#   render_upload()     — landing page with file uploader
#   render_analyzing()  — analysis spinner and routing
# -------------------------------------------------------------------------------

import os
import base64
import tempfile

import streamlit as st

from ui.shared import render_page_header, render_page_title, render_step_card
from analysis import analyze_pdf, preflight_check


def render_upload():
    """
    Purpose: Landing page — introduce the tool, show who made it, then let
    the user upload a PDF. WCAG 2.2 SC 1.3.1: file upload has an accessible label.
    """
    BC_MAROON = "#882346"
    BC_GRAY   = "#999799"

    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "BC_Logo_Library & Academic IT.png")

    logo_html = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = (
            f"<img src='data:image/png;base64,{logo_b64}' "
            "style='width:150px; height:auto; vertical-align:middle; margin:10px;' "
            "alt='Brooklyn College logo'>"
        )

    st.markdown(
        f"""
        <div>
            <div style='display:flex; align-items:center; gap:16px;'>
                {logo_html}
                <h1 class='landing-title'>
                    PDF Accessibility Assistant
                </h1>
            </div>
            <div style='
                text-align:left;
                font-family:"Roboto", sans-serif;
                font-size:13pt;
                letter-spacing:0.06em;
                color:#999799;
                margin:0 !important;
                padding-left:10px;
                padding-top:10px;
                line-height:1.4;
            '>
                Brooklyn College Academic IT &nbsp;&nbsp;|&nbsp;&nbsp; The City University of New York
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<hr style='border:none; border-top:2px solid {BC_GRAY}; margin:10px 0 16px 0;'>",
        unsafe_allow_html=True,
    )

    col_main, col_blank = st.columns([6, 1])
    with col_main:

        st.markdown(
            "This tool helps Brooklyn College and CUNY faculty find and fix accessibility "
            "problems in course PDF materials. It uses a **human-in-the-loop** approach — "
            "providing remediation guidance and empowering faculty to make informed decisions "
            "about their course content. PDFs are evaluated using **WCAG 2.2 Level AA** standards."
        )

        st.markdown(
            f"<p style='color:{BC_MAROON}; font-weight:600; margin:12px 0 8px 0;'>"
            "How it works</p>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            render_step_card("1", "Upload", "Choose a course PDF from your computer.")
        with c2:
            render_step_card("2", "Analyze", "The tool checks for issues and explains what it found.")
        with c3:
            render_step_card("3", "Fix & Download", "Work through each issue, then download the remediated file.")

        st.divider()

        ack_col, upload_col = st.columns([1, 2])
        with ack_col:
            st.markdown(
                """
                <style>
                [data-testid="stCheckbox"] {
                    padding-left: 1em;
                    padding-right: 1em;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            copyright_acknowledged = st.checkbox(
                "I confirm I have the right to upload this file and assume full "
                "responsibility for its content. PDF Assistant is not responsible "
                "for any copyrighted materials.",
                key="copyright_ack",
            )
            if not copyright_acknowledged:
                st.markdown(
                    "<p style='color:#882346; font-size:14pt; margin-top:6px;'>"
                    "Important: please check the box to enable file upload.</p>",
                    unsafe_allow_html=True,
                )
        with upload_col:
            st.markdown(
                f"<h3 style='color:{BC_MAROON}; margin:0 0 0 0;'>Choose a PDF file to check</h3>",
                unsafe_allow_html=True,
            )
            st.caption("This tool accepts PDF files only (.pdf).")
            uploaded_file = st.file_uploader(
                label="Choose a PDF file to check",
                type=["pdf"],
                help="Upload the course PDF you want to review for accessibility issues.",
                key="pdf_uploader",
                disabled=not copyright_acknowledged,
                label_visibility="hidden",
            )
            if copyright_acknowledged:
                st.caption(
                    "Once you upload your file, it may take a few minutes to analyze "
                    "depending on its size. Large files can take 5 minutes or more. "
                    "Please be patient — the tool is working."
                )

        if uploaded_file is not None and copyright_acknowledged:
            st.session_state.file_name = uploaded_file.name.strip()
            st.session_state.file_bytes = uploaded_file.read()
            st.session_state.working_pdf_bytes = st.session_state.file_bytes
            st.session_state.step = "analyzing"
            st.rerun()


def render_analyzing():
    """
    Purpose: Analyze the uploaded PDF and route to the correct next step.
    This step is transient — the user never stays here long.
    """
    render_page_header()
    render_page_title("Analyzing your document")

    preflight = preflight_check(
        output_paths=[tempfile.gettempdir()],
    )
    if not preflight["ok"]:
        st.error(
            "🔴 **Setup issue — cannot start analysis.**\n\n"
            + "\n\n".join(preflight["errors"])
        )
        if st.button("← Go back", type="primary"):
            st.session_state.step = "upload"
            st.rerun()
        return

    with st.spinner(f"Analyzing **{st.session_state.file_name}** — just a moment..."):
        result = analyze_pdf(st.session_state.file_bytes)

    st.session_state.docling_doc = result.get("docling_doc")

    if result["status"] == "password_protected":
        st.session_state.step = "password_protected"
    elif result["status"] == "scanned":
        st.session_state.cover_page_only = result.get("cover_page_only", False)
        st.session_state.step = "scanned_doc"
    elif result["status"] == "no_issues":
        st.session_state.step = "no_issues"
    else:
        st.session_state.issues = result["issues"]
        st.session_state.step = "issue_list"

    st.rerun()
