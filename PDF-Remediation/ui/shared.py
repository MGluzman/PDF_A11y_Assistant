"""Shared UI components."""

# -------------------------------------------------------------------------------
# ui/shared.py — constants and shared render helpers used by all UI modules
#
# Constants:
#   SEVERITY_LABELS  — display strings for Red/Yellow/Green severity codes
#
# Functions:
#   init_state()                  — set default values for all session_state keys
#   render_page_header()          — branded header shown at top of every screen
#   render_page_title()           — H1 title with refresh warning callout
#   render_step_card()            — numbered step card for "How it works" section
#   _render_go_back()             — linear ← Go back button
#   _render_abandon_button()      — ✕ Abandon current process escape button
#   _render_image_nav_buttons()   — Previous / Skip / Stop nav for alt text workflow
#   _advance_alt_text_image()     — move to next image or summary phase
# -------------------------------------------------------------------------------

import os
import base64

import streamlit as st


# Severity tier display strings — always pair text label with emoji icon
# so the UI never relies on color alone (WCAG 2.2 SC 1.4.1).
SEVERITY_LABELS = {
    "red":    "🔴 Red Light",
    "yellow": "🟡 Yellow Light",
    "green":  "🟢 Green Light",
}


def init_state():
    """Set default values for all session_state keys on first load."""
    defaults = {
        "step": "upload",
        "file_name": None,
        "file_bytes": None,
        "issues": [],
        "resolved_ids": [],
        "skipped_ids": [],
        "showing_alternative": False,
        "ocr_download_mode": False,
        "untagged_pdf_pending": False,
        "manual_review_results": {},
        "resolved_count": 0,
        "current_issue_id": None,
        "proposed_fix": None,
        "reanalysis_done": False,
        "cover_page_only": False,
        "ocr_pages_text": [],
        "ocr_docx_bytes": None,
        "ocr_pdf_bytes": None,
        "ocr_issues": [],
        "ocr_quality_score": None,
        "ocr_quality_label": None,
        "ocr_engine_used": None,
        "ocr_processing_log": [],
        "working_pdf_bytes": None,
        "alt_text_images": [],
        "alt_text_index": 0,
        "alt_text_phase": "question_1",
        "alt_text_results": {},
        "alt_text_auto_classifications": {},
        "docling_doc": None,
        "edited_docx_bytes": None,
        "edited_pdf_bytes":  None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_page_header():
    """
    Shared branding header shown at the top of every non-landing screen.
    Layout: [BC logo] | [2px gray vertical rule] | PDF Accessibility Assistant
    """
    BC_GRAY   = "#999799"
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "BC_Logo_Library & Academic IT.png")

    logo_html = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = (
            f"<img src='data:image/png;base64,{logo_b64}' "
            "style='width:120px; height:auto; display:block;' "
            "alt='Brooklyn College logo'>"
        )

    st.markdown(
        f"""
        <div style='display:flex; align-items:stretch; gap:14px; margin-bottom:8px;'>
            {logo_html}
            <div style='width:1px; background-color:#999799; flex-shrink:0;'></div>
            <div style='display:flex; align-items:center;'>
                <p style='color:#999799; font-size:1.15rem; font-weight:700;
                           margin:0; line-height:1.2;'>
                    PDF Accessibility Assistant
                </p>
            </div>
        </div>
        <hr style='border:none; border-top:1px solid {BC_GRAY}; margin:0 0 16px 0;'>
        """,
        unsafe_allow_html=True,
    )


def render_page_title(title):
    """
    Renders the H1 page title alongside a compact refresh warning callout.
    Layout within the 6/1 grid: [4] title | [2] warning box.
    """
    col_title, col_warn = st.columns([4, 2])
    with col_title:
        st.title(title)
    with col_warn:
        st.markdown(
            """
            <div style='
                background: #FFF8E1;
                border-left: 3px solid #F3BD48;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 0.75rem;
                line-height: 1.4;
                margin-top: 6px;
            '>
            ⚠️ <strong>Do not refresh this page.</strong>
            Refreshing will restart the session and you will lose your progress.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_step_card(number, title, description):
    """
    Render a styled step card for the 'How it works' section.
    Reusable: pass a step number, short title, and description text.
    """
    st.markdown(
        f"""
        <div style='
            background-color: #F0F2F6;
            border-left: 4px solid #F3BD48;
            border-radius: 6px;
            padding: 16px 20px 20px 20px;
            height: 100%;
        '>
            <div style='
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 10px;
            '>
                <div style='
                    flex-shrink: 0;
                    background-color: #882346;
                    color: white;
                    font-weight: 700;
                    font-size: 1rem;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    line-height: 40px;
                    text-align: center;
                '>{number}</div>
                <p style='
                    color: #882346;
                    font-weight: 600;
                    font-size: 1rem;
                    margin: 0;
                '>{title}</p>
            </div>
            <p style='
                color: #1A1A1A;
                font-size: 0.9rem;
                margin: 0;
            '>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_go_back(destination):
    """
    Render the linear "← Go back" button for non-remediation workflow screens.

    This is simple step navigation — it moves the user to the preceding screen
    without touching any session state beyond `step`. No work is lost.

    Parameters:
        destination (str): The step name to return to (e.g. "upload", "scanned_doc").
    """
    st.divider()
    if st.button("← Go back", key=f"go_back_{destination}"):
        st.session_state.step = destination
        st.rerun()


def _render_abandon_button():
    """
    Render the global "✕ Abandon current process" escape button.

    Shown at the bottom of every remediation and human-in-the-loop screen.
    Clicking it discards whatever is currently in progress (any uncommitted
    decision for the current issue/image) and returns to the issue list,
    which is always the last completed summary state.

    Completed work is never lost — resolved_ids and applied fixes remain in
    session state. Only the in-progress interaction is abandoned.
    """
    st.divider()
    if st.button(
        "✕ Abandon current process",
        use_container_width=False,
        key=f"abandon_{st.session_state.get('step', 'unknown')}_{st.session_state.get('alt_text_index', 0)}",
        help="Stop what you're doing and return to the issue list. Completed fixes are kept.",
    ):
        st.session_state.current_issue_id    = None
        st.session_state.proposed_fix        = None
        st.session_state.showing_alternative = False
        st.session_state.step                = "issue_list"
        st.rerun()


def _render_image_nav_buttons(index, total, img_key, current, results):
    """
    Render the three navigation buttons shown at the bottom of every per-image
    phase: Previous, Skip, and Stop.

    Parameters:
        index   (int):        0-based index of the current image.
        total   (int):        Total number of images in the workflow.
        img_key (int|str):    Key identifying the current image in alt_text_results.
        current (dict):       The current image's metadata dict.
        results (dict):       The live alt_text_results dict from session state.
    """
    st.divider()
    nav_cols = st.columns(3)

    with nav_cols[0]:
        if index > 0:
            if st.button(
                "← Previous image",
                use_container_width=True,
                key=f"nav_prev_{index}",
            ):
                results.pop(img_key, None)
                st.session_state.alt_text_results = results
                st.session_state.alt_text_index = index - 1
                st.session_state.alt_text_phase = "question_1"
                st.rerun()

    with nav_cols[1]:
        if st.button(
            "Skip this image →",
            use_container_width=True,
            key=f"nav_skip_{index}",
        ):
            _COMPLETE = {"decorative", "artifact", "background",
                         "edge_artifact", "informational"}
            if results.get(img_key, {}).get("type") not in _COMPLETE:
                results[img_key] = {
                    "type": "skipped",
                    "severity": "green",
                    "alt_text": "",
                    "page": current["page"],
                }
                st.session_state.alt_text_results = results
            _advance_alt_text_image()

    with nav_cols[2]:
        if st.button(
            "Skip fixing images",
            use_container_width=True,
            key=f"nav_stop_{index}",
        ):
            st.session_state.alt_text_phase = "summary"
            st.rerun()


def _advance_alt_text_image():
    """
    Move to the next image in the sequence, or to the summary phase when all
    images have been processed. Always resets the sub-phase to question_1 for
    the next image.
    """
    index      = st.session_state.alt_text_index
    total      = len(st.session_state.alt_text_images)
    next_index = index + 1
    if next_index >= total:
        st.session_state.alt_text_phase = "summary"
    else:
        st.session_state.alt_text_index = next_index
        st.session_state.alt_text_phase = "question_1"
    st.rerun()
