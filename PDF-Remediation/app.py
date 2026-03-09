# =============================================================================
# app.py — PDF Assistant (Streamlit)
# =============================================================================
# Purpose:
#   A step-by-step conversational tool that helps faculty identify and fix
#   accessibility barriers in PDF course materials to comply with:
#     - WCAG 2.1 Level AA (Web Content Accessibility Guidelines)
#     - Title II of the Americans with Disabilities Act (ADA)
#       as amended by DOJ regulations effective June 2024
#
# Architecture:
#   This is a Streamlit state machine. Streamlit re-runs this entire script
#   from top to bottom every time the user clicks a button or uploads a file.
#   We use st.session_state to remember where in the workflow the user is,
#   and what data has been collected so far.
#
#   The "step" key in session_state drives which screen is shown.
#   Each step is handled by a dedicated render_*() function below.
#
# How to run:
#   streamlit run app.py
# =============================================================================

import time                  # Used to simulate analysis time in placeholder logic
import fitz                  # PyMuPDF — opens PDFs, checks for password, detects scanned pages
import streamlit as st       # The main framework — builds the entire UI


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# Must be the FIRST Streamlit call in the script. Sets the browser tab title,
# icon, and layout. "wide" uses the full browser width — better for documents.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Assistant",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# DEMO ISSUE DATA
# =============================================================================
# In Phase 1, the analysis engine returns this hardcoded list of demo issues.
# In Phase 2, real PDF analysis libraries will generate this list dynamically.
#
# Each issue is a dictionary with:
#   id          — unique identifier used to track resolution
#   severity    — "red", "yellow", or "green" (drives display and ordering)
#   title       — short label shown in the issue list
#   description — explanation of why this matters for students
#   wcag        — WCAG 2.1 Success Criterion reference
#   ada         — Title II / 28 CFR Part 35 reference
#   fix_preview — sample text shown during the QA confirmation step
# =============================================================================
DEMO_ISSUES = [
    {
        "id": "missing_alt_text",
        "severity": "red",
        "title": "Images with missing text descriptions",
        "description": (
            "This document contains images that don't have text descriptions (also called "
            "alt text). Students who use screen readers — software that reads content aloud "
            "— won't be able to access the information those images convey."
        ),
        "wcag": "WCAG 2.1 SC 1.1.1 — Non-text Content",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've reviewed each image in your document and generated a text description "
            "for each one. I'll walk you through them one at a time so you can review "
            "and approve each description before it's saved."
        ),
    },
    {
        "id": "untagged_pdf",
        "severity": "red",
        "title": "Untagged PDF — no document structure",
        "description": (
            "This document has no accessibility tags. Tags are the behind-the-scenes "
            "structure that tells screen readers what is a heading, what is a paragraph, "
            "and what order to read things in. Without them, a screen reader user hears "
            "the content as an undifferentiated stream of text — or nothing at all."
        ),
        "wcag": "WCAG 2.1 SC 1.3.1 — Info and Relationships",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've analyzed the visual layout of your document and generated a tag "
            "structure that reflects the correct reading order and heading hierarchy. "
            "Here's a summary of the structure I'll apply."
        ),
    },
    {
        "id": "heading_hierarchy",
        "severity": "yellow",
        "title": "Incorrect or missing heading hierarchy",
        "description": (
            "The heading levels in this document are inconsistent — some levels are "
            "skipped, and the structure doesn't match what a reader would expect from "
            "the visual layout. Screen reader users navigate long documents by jumping "
            "between headings, so an incorrect hierarchy makes it hard to find content."
        ),
        "wcag": "WCAG 2.1 SC 1.3.1 — Info and Relationships",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've mapped your document's visual layout to a correct heading hierarchy "
            "(Heading 1 → Heading 2 → Heading 3) with no skipped levels. Here's the "
            "proposed structure."
        ),
    },
    {
        "id": "missing_lang",
        "severity": "yellow",
        "title": "Missing document language tag",
        "description": (
            "This document doesn't declare what language it's written in. Screen readers "
            "use the language tag to select the correct pronunciation rules and speech "
            "engine. Without it, text may be read aloud in the wrong language or with "
            "incorrect pronunciation — especially for technical terms and proper names."
        ),
        "wcag": "WCAG 2.1 SC 3.1.1 — Language of Page",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've detected that this document is written in English and will add the "
            "language tag 'en-US' to the document metadata."
        ),
    },
    {
        "id": "missing_title",
        "severity": "green",
        "title": "Missing document title in metadata",
        "description": (
            "The document's title field is empty — it currently defaults to the filename. "
            "Screen readers announce the document title when a file opens, and search "
            "tools use it for indexing. A descriptive title helps all users understand "
            "what they're looking at before they start reading."
        ),
        "wcag": "WCAG 2.1 SC 2.4.2 — Page Titled",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I'll add a descriptive title to the document metadata based on the content "
            "I found at the top of the first page. You can review and edit it before I save."
        ),
    },
    {
        "id": "missing_bookmarks",
        "severity": "green",
        "title": "Missing bookmarks / navigation",
        "description": (
            "This document is long enough that it would benefit from bookmarks — a "
            "clickable table of contents that lets readers jump directly to any section. "
            "Without bookmarks, everyone (not just screen reader users) has to scroll "
            "through the entire document to find what they need."
        ),
        "wcag": "WCAG 2.1 SC 2.4.5 — Multiple Ways",
        "ada": "Title II ADA, 28 CFR Part 35",
        "fix_preview": (
            "I've generated a bookmark list based on the heading structure in your "
            "document. Here's what it will look like in the navigation panel."
        ),
    },
]

# Labels and colors for each severity tier.
# We always pair the emoji icon with a text label (never icon alone).
# This is required by WCAG 2.1 SC 1.4.1 — Color Not Used as Only Visual Means.
SEVERITY_LABELS = {
    "red":    "🔴 Red Light",
    "yellow": "🟡 Yellow Light",
    "green":  "🟢 Green Light",
}


# =============================================================================
# PDF ANALYSIS — PLACEHOLDER (Phase 1)
# =============================================================================
# This function uses PyMuPDF to do two real checks:
#   1. Can the file be opened? (password protection)
#   2. Does the first page have any selectable text? (scanned/image-based check)
#
# If those checks pass, it returns the hardcoded DEMO_ISSUES list.
# In Phase 2, this function will be replaced with real analysis logic.
# =============================================================================

def analyze_pdf(file_bytes):
    """
    Analyze a PDF file and return a result dict describing what was found.

    Parameters:
        file_bytes (bytes): The raw bytes of the uploaded PDF file.

    Returns:
        dict with keys:
            status  — "password_protected" | "scanned" | "no_issues" | "issues_found"
            issues  — list of issue dicts (empty if status is not "issues_found")
    """
    try:
        # fitz.open() with a stream parameter reads from bytes in memory.
        # If the file is password-protected and cannot be opened, PyMuPDF
        # raises a fitz.FileDataError or returns a document that needs a password.
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # Check if the document requires a password to access content.
        # doc.needs_pass is True when the file is encrypted and unreadable.
        if doc.needs_pass:
            return {"status": "password_protected", "issues": []}

        # Check whether the first page contains any selectable (real) text.
        # Scanned documents render pages as images — get_text() returns empty
        # string "" because there are no text characters embedded in the file.
        if len(doc) > 0:
            first_page_text = doc[0].get_text().strip()
            if not first_page_text:
                # Page 1 has no selectable text.
                #
                # We sample page 2 (if it exists) to distinguish between two
                # scenarios:
                #   a) cover_page_only=True  — page 1 is a graphic cover image
                #      but page 2 has real text (rest of doc is likely readable)
                #   b) cover_page_only=False — both pages are unreadable, so the
                #      document is almost certainly fully scanned throughout
                #
                # Design decision: in BOTH cases we stop analysis and require
                # OCR first. Any unreadable page means we cannot guarantee a
                # complete analysis, and OCR can restructure content in ways
                # that would invalidate fixes applied beforehand.
                # The flag is stored so messaging can be tailored later.
                cover_page_only = len(doc) > 1 and bool(doc[1].get_text().strip())
                doc.close()
                return {"status": "scanned", "issues": [], "cover_page_only": cover_page_only}

        doc.close()

    except Exception:
        # If PyMuPDF raises any other error opening the file, treat it as
        # password-protected (safest fallback — don't crash the app).
        return {"status": "password_protected", "issues": []}

    # Phase 1 placeholder: always return the full demo issue list.
    # Phase 2 will replace this with real analysis results.
    return {"status": "issues_found", "issues": DEMO_ISSUES}


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# st.session_state persists between Streamlit re-runs for the same browser
# session. We initialize any keys that don't exist yet on the very first run.
# =============================================================================

def init_state():
    """Set default values for all session_state keys on first load."""
    defaults = {
        "step": "upload",           # Current workflow step
        "file_name": None,          # Original uploaded file name
        "file_bytes": None,         # Raw bytes of the uploaded file
        "issues": [],               # Full list of issue dicts from analysis
        "resolved_ids": [],         # List of issue IDs the user has resolved
        "resolved_count": 0,        # Running count of resolved issues (drives re-analysis)
        "current_issue_id": None,   # ID of the issue currently being worked on
        "proposed_fix": None,       # Text of the fix shown during QA confirmation
        "reanalysis_done": False,   # Whether re-analysis was offered at the current checkpoint
        "cover_page_only": False,   # True if only page 1 is unreadable (page 2 has text)
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()


# =============================================================================
# SIDEBAR
# =============================================================================
# The sidebar is always visible. It holds settings and a Start Over button.
# We use st.sidebar as a context manager (the 'with' block) so everything
# inside appears in the sidebar panel on the left.
# =============================================================================

with st.sidebar:
    st.header("⚙️ Settings")

    # Tesseract OCR path — pytesseract needs to know where the binary lives.
    # This path will be read by the OCR step in Phase 2.
    st.text_input(
        label="Tesseract OCR Path",
        value=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        help="Path to tesseract.exe. Download from: https://github.com/UB-Mannheim/tesseract/wiki",
        key="tesseract_path",
    )

    st.divider()

    # "Start Over" button — only show it when the user is past the upload step.
    # Clicking it resets all session state and returns to the upload screen.
    if st.session_state.step != "upload":
        if st.button("↩ Start Over", use_container_width=True):
            # Reset every key back to its default value by clearing state
            # and re-running init_state (which sets the defaults again).
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_state()
            st.rerun()

    st.divider()

    # Severity system explainer — shown once in the sidebar as reference.
    # Per WCAG 2.1 SC 1.4.1, we always pair the color indicator with text.
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

    st.markdown(
        """
        **About this tool**

        Built to support faculty in making digital course content accessible
        under **Title II of the ADA** (28 CFR Part 35), effective
        April 24, 2026 for large public institutions.

        Version 0.2 — Phase 1
        """
    )


# =============================================================================
# RENDER FUNCTIONS — one per workflow step
# =============================================================================
# Each function below handles one step in the workflow. It renders the UI
# for that step and sets up the buttons that transition to the next step.
#
# Pattern for transitioning:
#   st.session_state.step = "next_step_name"
#   st.rerun()   ← tells Streamlit to re-run the script from the top
# =============================================================================


# -----------------------------------------------------------------------------
# STEP: upload
# The starting screen. Shows a file uploader. When a PDF is uploaded,
# store the file data in session state and move to "analyzing".
# -----------------------------------------------------------------------------
def render_upload():
    """
    Purpose: Let the user upload a PDF.
    WCAG reference: File upload control has an accessible label (SC 1.3.1).
    """
    st.title("♿ PDF Assistant")
    st.markdown(
        "Upload a course PDF and I'll check it for accessibility issues that may "
        "create barriers for your students. I'll walk you through any fixes step by step."
    )
    st.divider()

    uploaded_file = st.file_uploader(
        label="Choose a PDF file to check",
        type=["pdf"],
        help="Upload the course PDF you want to review for accessibility issues.",
        key="pdf_uploader",
    )

    if uploaded_file is not None:
        # Store the file name and raw bytes in session state so we can
        # access them in later steps even after Streamlit re-renders.
        st.session_state.file_name = uploaded_file.name
        st.session_state.file_bytes = uploaded_file.read()
        st.session_state.step = "analyzing"
        st.rerun()


# -----------------------------------------------------------------------------
# STEP: analyzing
# Shows a spinner while we call analyze_pdf(), then routes to the appropriate
# next step based on what the analysis found.
# -----------------------------------------------------------------------------
def render_analyzing():
    """
    Purpose: Analyze the uploaded PDF and route to the correct next step.
    This step is transient — the user never stays here long.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    with st.spinner(f"Analyzing **{st.session_state.file_name}** — just a moment..."):
        # Simulate a brief delay so the spinner is visible.
        # In Phase 2 this delay will be replaced by actual processing time.
        time.sleep(1.5)
        result = analyze_pdf(st.session_state.file_bytes)

    # Route to the correct next step based on what was found.
    if result["status"] == "password_protected":
        st.session_state.step = "password_protected"
    elif result["status"] == "scanned":
        # Store whether only the cover page was unreadable vs. the whole doc.
        # Used by render_scanned_doc() for tailored messaging.
        st.session_state.cover_page_only = result.get("cover_page_only", False)
        st.session_state.step = "scanned_doc"
    elif result["status"] == "no_issues":
        st.session_state.step = "no_issues"
    else:
        # Store the issues list and go to the issue list screen.
        st.session_state.issues = result["issues"]
        st.session_state.step = "issue_list"

    st.rerun()


# -----------------------------------------------------------------------------
# STEP: password_protected
# Verbatim message from CLAUDE.md. Offers two choices.
# -----------------------------------------------------------------------------
def render_password_protected():
    """
    Purpose: Inform the user the file is password protected and offer options.
    Per CLAUDE.md: never ask for the password. Offer guidance instead.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Security warning — verbatim from CLAUDE.md
    st.warning(
        "⚠️ **DO NOT share your password or any other credentials in this tool.**"
    )

    st.info(
        "It looks like this file is password protected, which means I'm not able to "
        "read or analyze its contents. If you are the original author of this document, "
        "I can walk you through saving a new version of it without the password protection "
        "— just let me know. If someone else created this file, you may need to reach out "
        "to them or your IT support team to get an unlocked version."
    )

    st.markdown("**How would you like to proceed?**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, walk me through it.",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.step = "password_walkthrough"
            st.rerun()
    with col2:
        if st.button(
            "I'll take care of it another way.",
            use_container_width=True,
        ):
            st.session_state.step = "done"
            st.session_state.done_reason = "password_exit"
            st.rerun()


# -----------------------------------------------------------------------------
# STEP: password_walkthrough
# Step-by-step instructions for removing password protection. Then prompt
# the user to re-upload the unlocked file.
# -----------------------------------------------------------------------------
def render_password_walkthrough():
    """
    Purpose: Guide the user through removing password protection.
    After following the steps, the user returns to upload a new file.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    st.markdown(
        "Here's how to remove password protection in the most common applications:"
    )

    with st.expander("Adobe Acrobat", expanded=True):
        st.markdown(
            """
            1. Open your PDF in Adobe Acrobat.
            2. Go to **File → Properties → Security**.
            3. Change the Security Method to **No Security**.
            4. Click **OK**, then save the file (**File → Save As**) with a new name.
            5. Upload the new file here.
            """
        )

    with st.expander("Microsoft Word"):
        st.markdown(
            """
            1. Open the file in Word (it may prompt for the password to open it).
            2. Go to **File → Info → Protect Document → Encrypt with Password**.
            3. Delete the password field and click **OK**.
            4. Save the file as PDF: **File → Save As → PDF**.
            5. Upload the new file here.
            """
        )

    with st.expander("macOS Preview"):
        st.markdown(
            """
            1. Open the PDF in Preview. Enter the password when prompted.
            2. Go to **File → Export as PDF**.
            3. In the save dialog, click **Security Options** and remove the password.
            4. Save and upload the new file here.
            """
        )

    with st.expander("Google Drive"):
        st.markdown(
            """
            1. Upload the password-protected PDF to Google Drive.
            2. Right-click it and choose **Open with → Google Docs**.
            3. Google Docs will convert it. Go to **File → Download → PDF Document**.
            4. Upload the downloaded file here.
            """
        )

    st.divider()
    st.markdown("Once you have an unlocked version, click below to start over and upload it.")

    if st.button("↩ Upload a new file", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_state()
        st.rerun()


# -----------------------------------------------------------------------------
# STEP: scanned_doc
# Verbatim Red Light message from CLAUDE.md. Offers two choices.
# -----------------------------------------------------------------------------
def render_scanned_doc():
    """
    Purpose: Inform the user the document contains scanned (image-based) text
    and stop analysis until OCR is complete.

    This is a Red Light issue — the most serious category.

    The 2-page detection logic in analyze_pdf() may have determined that only
    the cover page is unreadable (cover_page_only=True) vs. the full document.
    Either way, analysis is stopped and OCR is required before proceeding.

    Accessibility note: the "ANALYSIS STOPPED" label uses text, not color alone,
    to communicate the severity — per WCAG 2.1 SC 1.4.1.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Tailor the opening line slightly based on whether only the cover is unreadable.
    # Both cases stop analysis — but the description is more accurate this way.
    if st.session_state.cover_page_only:
        scope_note = (
            "At least one page of your PDF contains text that was scanned as an image."
        )
    else:
        scope_note = (
            "Your PDF contains text that was scanned as an image."
        )

    # "ANALYSIS STOPPED" callout — pairs text label with color (WCAG SC 1.4.1)
    st.error(
        f"🔴 **ANALYSIS STOPPED — {SEVERITY_LABELS['red']} Issue**\n\n"
        f"{scope_note} This creates serious accessibility barriers for most users: "
        "screen readers cannot read image-based text, students cannot search or copy "
        "it, and it cannot be resized or translated. "
        "This document cannot be analyzed or improved until it is converted to a "
        "readable PDF.\n\n"
        "**Would you like me to convert it now?**"
    )

    # Standards reference — supporting context, not the lead reason to act
    st.caption(
        "WCAG 2.1 SC 1.4.5 — Images of Text | Title II ADA, 28 CFR Part 35"
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


# -----------------------------------------------------------------------------
# STEP: scanned_goodbye
# Shown when the user declines OCR conversion on a scanned document.
# Offers two exit paths: upload a different file or end the session entirely.
# -----------------------------------------------------------------------------
def render_scanned_goodbye():
    """
    Purpose: Close the session gracefully when the user chooses not to convert
    their scanned document.

    Two choices:
      - Upload another file — resets state and returns to the upload screen
      - No, I'm done for now — ends the session
    """
    st.title("♿ PDF Assistant")
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
            # Reset all session state and return to the upload screen.
            # This is the same reset pattern used by "Start Over" in the sidebar.
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


# -----------------------------------------------------------------------------
# STEP: running_ocr
# Placeholder OCR step. Shows a spinner, then transitions to issue_list.
# In Phase 2, this will call pytesseract or easyocr.
# -----------------------------------------------------------------------------
def render_running_ocr():
    """
    Purpose: Run OCR on the scanned document (Phase 1: placeholder spinner).
    After OCR, re-analyze the converted text and go to the issue list.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    with st.spinner(
        "Converting your scanned pages to readable text — this may take a moment "
        "for longer documents..."
    ):
        # Phase 1 placeholder: simulate OCR processing time.
        # Phase 2 will replace this with pytesseract / easyocr processing.
        time.sleep(2.5)

    st.success("Conversion complete! Now analyzing the readable text for accessibility issues...")
    time.sleep(1)

    # After OCR, proceed to show the issue list (using demo issues for Phase 1).
    st.session_state.issues = DEMO_ISSUES
    st.session_state.step = "issue_list"
    st.rerun()


# -----------------------------------------------------------------------------
# STEP: no_issues
# Verbatim clean document message from CLAUDE.md.
# -----------------------------------------------------------------------------
def render_no_issues():
    """
    Purpose: Tell the user the document looks good. Offer download or end session.
    Verbatim message from CLAUDE.md.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Verbatim message from CLAUDE.md
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
            # Offer the original file as a download since no changes were made.
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


# -----------------------------------------------------------------------------
# STEP: issue_list
# Shows the prioritized issue list grouped by severity.
# The user clicks any issue to begin working on it.
# -----------------------------------------------------------------------------
def render_issue_list():
    """
    Purpose: Present all remaining issues, grouped by severity (Red → Yellow → Green).
    User clicks any issue to start resolving it in any order they choose.
    Per CLAUDE.md: display the Priority Recommendation message verbatim first.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Count remaining unresolved issues
    remaining = [
        issue for issue in st.session_state.issues
        if issue["id"] not in st.session_state.resolved_ids
    ]

    if not remaining:
        # All issues resolved — move to format selection
        st.session_state.step = "choose_format"
        st.rerun()
        return

    # File context
    st.markdown(f"**File:** {st.session_state.file_name}")

    # Priority Recommendation — verbatim from CLAUDE.md
    st.info(
        "We strongly recommend starting with the Red Light and Yellow Light issues. "
        "These create the most significant barriers for your students and are the ones "
        "that bring your document into compliance with Title II accessibility requirements. "
        "Where would you like to start?"
    )

    # Group remaining issues by severity for display
    # Order: red first, then yellow, then green — most serious to least serious
    for severity in ["red", "yellow", "green"]:
        severity_issues = [i for i in remaining if i["severity"] == severity]
        if not severity_issues:
            continue

        st.markdown(f"### {SEVERITY_LABELS[severity]}")

        for issue in severity_issues:
            # Each issue renders as a clickable button.
            # The button label is the issue title.
            if st.button(
                f"{issue['title']}",
                key=f"issue_btn_{issue['id']}",
                use_container_width=True,
            ):
                st.session_state.current_issue_id = issue["id"]
                st.session_state.proposed_fix = issue["fix_preview"]
                st.session_state.step = "resolving_issue"
                st.rerun()

        st.markdown("")  # Spacing between severity groups

    # Progress indicator
    total = len(st.session_state.issues)
    resolved = len(st.session_state.resolved_ids)
    st.divider()
    st.caption(f"{resolved} of {total} issues resolved")


# -----------------------------------------------------------------------------
# STEP: resolving_issue
# Shows the issue details, applies a placeholder fix, then goes to QA step.
# -----------------------------------------------------------------------------
def render_resolving_issue():
    """
    Purpose: Show the selected issue and its proposed fix for faculty review.
    Per CLAUDE.md Per-Issue QA Process:
      Step 1 — Internal self-check (not shown to user — we simulate this).
      Step 2 — Faculty confirmation with exact verbatim message.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Find the current issue by ID
    issue = next(
        (i for i in st.session_state.issues if i["id"] == st.session_state.current_issue_id),
        None,
    )

    if issue is None:
        # Safety net: if we can't find the issue, go back to the list
        st.session_state.step = "issue_list"
        st.rerun()
        return

    # Show which issue we're working on
    st.markdown(f"### {SEVERITY_LABELS[issue['severity']]} — {issue['title']}")
    st.markdown(f"*{issue['wcag']} | {issue['ada']}*")
    st.divider()

    # Explain the issue and why it matters
    st.markdown("**Why this matters for your students:**")
    st.markdown(issue["description"])

    st.divider()

    # Show the proposed fix (Phase 1: placeholder description from issue data)
    st.markdown("**Here's what I changed. Does this look right to you?**")
    st.info(issue["fix_preview"])

    # Faculty confirmation — exactly two choices per CLAUDE.md
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, that looks good.",
            type="primary",
            use_container_width=True,
            key="confirm_yes",
        ):
            # Mark this issue as resolved
            st.session_state.resolved_ids.append(issue["id"])
            st.session_state.resolved_count += 1
            st.session_state.current_issue_id = None
            st.session_state.proposed_fix = None

            # Check if we've hit a multiple of 3 — offer re-analysis
            # Per CLAUDE.md: "After every three issues have been resolved, offer a re-analysis"
            if (
                st.session_state.resolved_count % 3 == 0
                and not st.session_state.reanalysis_done
            ):
                st.session_state.step = "re_analysis"
            else:
                st.session_state.reanalysis_done = False
                st.session_state.step = "continue_or_stop"

            st.rerun()

    with col2:
        if st.button(
            "No, let's try again.",
            use_container_width=True,
            key="confirm_no",
        ):
            # Return to the issue list without marking as resolved.
            # In Phase 2, this would offer an alternative fix approach.
            st.session_state.current_issue_id = None
            st.session_state.step = "issue_list"
            st.rerun()


# -----------------------------------------------------------------------------
# STEP: continue_or_stop
# After each resolved issue, ask whether to keep going or stop.
# -----------------------------------------------------------------------------
def render_continue_or_stop():
    """
    Purpose: Give the user a natural pause after each resolved issue.
    Per CLAUDE.md: ask "keep going?" after every issue.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    resolved = len(st.session_state.resolved_ids)
    remaining = len(st.session_state.issues) - resolved

    st.success(f"Issue resolved! You've fixed {resolved} issue(s) so far.")

    if remaining > 0:
        st.markdown(
            f"There {'is' if remaining == 1 else 'are'} still "
            f"**{remaining}** issue{'s' if remaining != 1 else ''} remaining. "
            "Would you like to keep going?"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, let's keep going.",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.step = "issue_list"
                st.rerun()
        with col2:
            if st.button(
                "No, I'm done for now.",
                use_container_width=True,
            ):
                st.session_state.step = "choose_format"
                st.rerun()
    else:
        # No issues remaining — go straight to format selection
        st.markdown("You've worked through all the issues — great job!")
        if st.button("Continue to download", type="primary"):
            st.session_state.step = "choose_format"
            st.rerun()


# -----------------------------------------------------------------------------
# STEP: re_analysis
# Offered after every 3 resolved issues per CLAUDE.md.
# -----------------------------------------------------------------------------
def render_re_analysis():
    """
    Purpose: Offer to re-analyze the document after every 3 resolved issues.
    Per CLAUDE.md: verbatim message and exactly two choices.
    Phase 1: re-analysis is simulated (same demo issue list).
    """
    st.title("♿ PDF Assistant")
    st.divider()

    # Verbatim message from CLAUDE.md
    st.info(
        "You've made some good progress — fixing some of these issues can sometimes "
        "resolve others automatically. Would you like me to take another look at the "
        "document to see if anything else has been taken care of?"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, check it again.",
            type="primary",
            use_container_width=True,
        ):
            # Phase 1: simulate re-analysis (no actual change to issue list).
            # Phase 2: re-run the real analysis on the working file.
            with st.spinner("Re-analyzing your document..."):
                time.sleep(1.5)
            st.session_state.reanalysis_done = True
            st.session_state.step = "issue_list"
            st.rerun()
    with col2:
        if st.button(
            "No, let's keep going.",
            use_container_width=True,
        ):
            st.session_state.reanalysis_done = True
            st.session_state.step = "continue_or_stop"
            st.rerun()


# -----------------------------------------------------------------------------
# STEP: choose_format
# Ask whether the user wants DOCX or PDF output.
# Per CLAUDE.md: deliver the file with "_edited" appended to the original name.
# -----------------------------------------------------------------------------
def render_choose_format():
    """
    Purpose: Let the user choose their output format (DOCX or PDF).
    Per CLAUDE.md: file name gets "_edited" appended before the extension.
    Phase 1: delivers the original file as a placeholder download.
    """
    st.title("♿ PDF Assistant")
    st.divider()

    resolved = len(st.session_state.resolved_ids)
    st.success(f"Great work — you've resolved {resolved} accessibility issue(s).")

    st.markdown(
        "What format would you like for your updated file? "
        "I'll save it with your original file name, with **_edited** added at the end."
    )

    # Build the output file names for display
    base_name = st.session_state.file_name.replace(".pdf", "").replace(".PDF", "")
    docx_name = f"{base_name}_edited.docx"
    pdf_name = f"{base_name}_edited.pdf"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Word processor document (DOCX)**")
        st.caption(
            "Opens in Microsoft Word, Google Docs, or any compatible application. "
            "Best if you need to edit the content further before re-publishing."
        )
        if st.button(f"Download as {docx_name}", type="primary", use_container_width=True):
            # Phase 1 placeholder: download the original file bytes.
            # Phase 2 will generate a real DOCX with all fixes applied.
            st.download_button(
                label=f"Click here to download {docx_name}",
                data=st.session_state.file_bytes,
                file_name=docx_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    with col2:
        st.markdown("**New PDF document**")
        st.caption(
            "A properly structured, text-based PDF ready to share or upload directly. "
            "Best if you want a finished file."
        )
        if st.button(f"Download as {pdf_name}", use_container_width=True):
            # Phase 1 placeholder: download the original file bytes.
            # Phase 2 will generate a real remediated PDF.
            st.download_button(
                label=f"Click here to download {pdf_name}",
                data=st.session_state.file_bytes,
                file_name=pdf_name,
                mime="application/pdf",
            )


# -----------------------------------------------------------------------------
# STEP: done
# Session end screen. Shown when the user exits without completing all issues.
# -----------------------------------------------------------------------------
def render_done():
    """
    Purpose: Gracefully end the session.
    Shown when user chooses to walk away (password, scanned doc) or finishes.
    """
    st.title("♿ PDF Assistant")
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


# =============================================================================
# MAIN ROUTER
# =============================================================================
# This is the traffic director. It reads the current "step" from session_state
# and calls the matching render function. Streamlit re-runs this entire block
# on every user interaction, so the right screen always appears.
# =============================================================================

STEP_HANDLERS = {
    "upload":               render_upload,
    "analyzing":            render_analyzing,
    "password_protected":   render_password_protected,
    "password_walkthrough": render_password_walkthrough,
    "scanned_doc":          render_scanned_doc,
    "scanned_goodbye":      render_scanned_goodbye,
    "running_ocr":          render_running_ocr,
    "no_issues":            render_no_issues,
    "issue_list":           render_issue_list,
    "resolving_issue":      render_resolving_issue,
    "continue_or_stop":     render_continue_or_stop,
    "re_analysis":          render_re_analysis,
    "choose_format":        render_choose_format,
    "done":                 render_done,
}

# Call the render function for the current step.
# If somehow step is set to an unknown value, fall back to upload.
handler = STEP_HANDLERS.get(st.session_state.step, render_upload)
handler()


# -----------------------------------------------------------------------------
# FOOTER
# Always visible at the bottom of every screen.
# Provides legal context without being the lead message.
# -----------------------------------------------------------------------------
st.divider()
st.caption(
    "PDF Assistant supports compliance with **Title II of the ADA** (28 CFR Part 35) "
    "and **WCAG 2.1 Level AA**. It provides guidance and analysis but does not "
    "constitute legal advice. Always consult your institution's accessibility office."
)
