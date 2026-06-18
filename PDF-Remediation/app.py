# =============================================================================
# app.py — PDF Assistant (Streamlit)
# =============================================================================
# Purpose:
#   A step-by-step conversational tool that helps faculty identify and fix
#   accessibility barriers in PDF course materials to comply with:
#     - WCAG 2.2 Level AA (Web Content Accessibility Guidelines)
#     - Title II of the Americans with Disabilities Act (ADA)
#       as amended by DOJ regulations effective June 2024
#
# Architecture:
#   This is a Streamlit state machine. Streamlit re-runs this entire script
#   from top to bottom every time the user clicks a button or uploads a file.
#   st.session_state["step"] drives which screen is shown. Each screen is
#   a render_*() function defined in a focused module under ui/.
#
# Module layout:
#   ocr.py          — Tesseract / EasyOCR pipeline
#   analysis.py     — PDF analysis, preflight check, Docling integration
#   images.py       — image extraction and auto-classification
#   fixes.py        — per-issue fix functions + FIX_DISPATCH
#   docx_export.py  — DOCX build and Word-based PDF conversion
#   ui/shared.py    — SEVERITY_LABELS, init_state(), shared render helpers
#   ui/upload.py    — upload and analyzing screens
#   ui/password.py  — password protection screens
#   ui/scanned.py   — scanned doc, OCR, format select screens
#   ui/issues.py    — issue list, fix, re-analysis, continue/stop screens
#   ui/images_ui.py — alt text workflow + render_issue_panels/render_plan_box
#   ui/manual_review.py — manual checklist screen
#   ui/done.py      — no-issues, choose format, done screens
#
# How to run:
#   streamlit run app.py
# =============================================================================

import streamlit as st

# st.set_page_config() MUST be the first Streamlit call — placed here, before
# any module imports that might trigger st calls indirectly.
st.set_page_config(
    page_title="PDF Assistant",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import all public symbols from every module. Import order matches the
# dependency graph: lower-level modules first so higher-level ones can
# safely reference their symbols at definition time.
from ocr import *
from analysis import *
from images import *
from fixes import *
from docx_export import *
from ui.shared import *
from ui.upload import *
from ui.password import *
from ui.scanned import *
from ui.issues import *
from ui.images_ui import *
from ui.manual_review import *
from ui.done import *

# Initialize session state on first load (init_state is defined in ui/shared.py).
init_state()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    if st.session_state.step != "upload":
        if st.button("↩ Start Over", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_state()
            st.rerun()

    st.divider()

    # Per WCAG 2.2 SC 1.4.1: severity labels always pair color indicator with text.
    st.markdown(
        """
        **About issue severity**

        🔴 **Red Light** — Serious issues that create significant obstacles
        for some or all of your students.

        🟡 **Yellow Light** — Important issues required for accessibility
        compliance under Title II of the ADA.

        🟢 **Green Light** — Finishing touches that bring your document
        to full compliance.
        """
    )

    st.divider()

    st.markdown("**Compliance Updates**")
    st.info(
        "**NYS deadline:** CUNY must meet WCAG 2.2 Level AA by "
        "**January 1, 2027** under Title II of the ADA (28 CFR Part 35).",
        icon="📅",
    )

    st.divider()
    with st.expander("⚙️ Advanced", expanded=False):
        st.caption(
            "Only change this if Tesseract OCR is installed in a non-default location."
        )
        st.text_input(
            label="Tesseract path",
            value=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            help="Path to tesseract.exe. Download from: https://github.com/UB-Mannheim/tesseract/wiki",
            key="tesseract_path",
            label_visibility="collapsed",
        )


# =============================================================================
# STEP ROUTER
# =============================================================================

STEP_HANDLERS = {
    "upload":               render_upload,
    "analyzing":            render_analyzing,
    "password_protected":   render_password_protected,
    "password_walkthrough": render_password_walkthrough,
    "scanned_doc":          render_scanned_doc,
    "scanned_goodbye":      render_scanned_goodbye,
    "running_ocr":          render_running_ocr,
    "running_easyocr":      render_running_easyocr,
    "ocr_format_select":    render_ocr_format_select,
    "no_issues":            render_no_issues,
    "issue_list":           render_issue_list,
    "image_alt_text":       render_image_alt_text,
    "source_file_question": render_source_file_question,
    "cuny_resources":       render_cuny_resources,
    "resolving_issue":      render_resolving_issue,
    "continue_or_stop":     render_continue_or_stop,
    "re_analysis":          render_re_analysis,
    "manual_review":        render_manual_review,
    "choose_format":        render_choose_format,
    "done":                 render_done,
}

# Global style overrides — applied once per render, affect all screens.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400&family=Roboto+Slab:wght@700&display=swap');

    .block-container {
        padding-top: 3rem !important;
    }
    h1 {
        font-family: 'Roboto Slab', Georgia, serif !important;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        color: #882346 !important;
    }
    h1.landing-title {
        font-family: sans-serif !important;
        font-size: 24pt !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
        color: #882346 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    h2 {
        font-family: 'Roboto', sans-serif !important;
        font-size: 1.35rem !important;
        font-weight: 400 !important;
        color: #999799 !important;
    }
    h3 {
        color: #882346 !important;
        font-size: 1.17rem !important;
    }
    [data-testid="stFileUploader"] {
        margin-top: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        border: 2px solid #882346 !important;
        border-radius: 6px !important;
        min-height: 120px !important;
        margin-top: 0 !important;
    }
    [data-testid="stFileUploader"] .stMarkdown {
        margin-bottom: 0 !important;
    }

    /* Issue panel boxes — used by render_issue_panels() in ui/images_ui.py */
    .issue-box-wrapper {
        max-width: clamp(320px, 80%, 860px);
        margin-left: auto;
        margin-right: auto;
        margin-bottom: 12px;
    }
    .issue-why-box {
        background-color: #ffffff;
        border: 1px solid #999799;
        border-radius: 6px;
        padding: 16px 18px;
        height: 100%;
    }
    .issue-plan-box {
        background-color: #ffffff;
        border: 1px solid #882346;
        border-radius: 6px;
        padding: 16px 18px;
        height: 100%;
    }
    .issue-box-label {
        font-size: 1.15rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #999799;
        margin-bottom: 8px;
    }
    .issue-plan-box .issue-box-label {
        color: #882346;
    }

    [data-testid="stBaseButton-primary"],
    .stButton > button[kind="primary"] {
        background-color: rgba(136, 35, 70, 0.70) !important;
        color: #ffffff !important;
        border: none !important;
        transition: background-color 0.15s ease !important;
    }
    [data-testid="stBaseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        background-color: #882346 !important;
        color: #ffffff !important;
        border: none !important;
    }
    [data-testid="stBaseButton-primary"]:active,
    .stButton > button[kind="primary"]:active {
        background-color: #882346 !important;
        color: #ffffff !important;
        border: none !important;
    }

    [data-testid="stBaseButton-secondary"],
    .stButton > button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #999799 !important;
        transition: background-color 0.15s ease !important;
    }
    [data-testid="stBaseButton-secondary"]:hover,
    .stButton > button[kind="secondary"]:hover {
        background-color: #F0F2F6 !important;
        color: #000000 !important;
        border: 1px solid #999799 !important;
    }
    [data-testid="stBaseButton-secondary"]:active,
    .stButton > button[kind="secondary"]:active {
        background-color: #F0F2F6 !important;
        color: #000000 !important;
        border: 1px solid #999799 !important;
    }

    [data-testid="stBaseButton-primary"] p,
    [data-testid="stBaseButton-secondary"] p,
    .stButton > button p {
        font-family: "Roboto Slab", serif !important;
        font-size: 1.15rem !important;
    }

    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"],
    .stButton > button {
        margin-top: 1.25rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Route to the current step's render function. Falls back to upload if step
# is somehow set to an unrecognized value.
handler = STEP_HANDLERS.get(st.session_state.step, render_upload)
handler()
