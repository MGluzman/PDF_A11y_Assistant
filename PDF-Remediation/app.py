# =============================================================================
# app.py — PDF Accessibility Remediation Tool (Streamlit)
# =============================================================================
# Purpose:
#   A web-based tool that helps faculty identify and fix accessibility
#   barriers in PDF course materials to comply with:
#     - WCAG 2.1 Level AA (Web Content Accessibility Guidelines)
#     - Title II of the Americans with Disabilities Act (ADA)
#       as amended by DOJ regulations effective June 2024
#
# Architecture Overview:
#   This is a single-page Streamlit app. Streamlit works by re-running
#   this entire script top-to-bottom every time the user interacts with
#   a widget (clicks a button, uploads a file, etc.). Streamlit manages
#   the UI state between runs using st.session_state.
#
# How to run:
#   streamlit run app.py
# =============================================================================

import streamlit as st  # The main framework — builds the entire UI


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# Must be the FIRST Streamlit call in the script.
# Sets the browser tab title, icon, and layout width.
# "wide" layout uses the full browser width — better for document tools.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Accessibility Remediation Tool",
    page_icon="♿",          # Appears in the browser tab
    layout="wide",           # Uses full browser width
    initial_sidebar_state="expanded",  # Sidebar open by default
)


# -----------------------------------------------------------------------------
# HEADER SECTION
# st.title() renders an <h1> element.
# st.markdown() allows HTML/Markdown for richer formatting.
# -----------------------------------------------------------------------------
st.title("♿ PDF Accessibility Remediation Tool")
st.markdown(
    """
    Help faculty make course PDFs compliant with **WCAG 2.1 Level AA** and
    **Title II of the ADA**. Upload a PDF to begin the accessibility audit.
    """
)

# A horizontal rule to visually separate the header from the main content
st.divider()


# -----------------------------------------------------------------------------
# SIDEBAR — Settings & Navigation
# The sidebar is always visible on the left. It's a good place for settings
# that the user may need to adjust without losing their place in the workflow.
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    # Tesseract path setting
    # pytesseract needs to know where the Tesseract binary is installed.
    # st.text_input() creates a single-line text field.
    # The value is stored in st.session_state automatically via the 'key' param.
    tesseract_path = st.text_input(
        label="Tesseract OCR Path",
        value=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        help="Path to tesseract.exe. Download from: https://github.com/UB-Mannheim/tesseract/wiki",
        key="tesseract_path",
    )

    st.divider()

    # Accessibility standard selector
    # st.multiselect() lets the user pick one or more options.
    standards = st.multiselect(
        label="Check Against Standards",
        options=["WCAG 2.1 AA", "PDF/UA-1", "Title II ADA"],
        default=["WCAG 2.1 AA", "Title II ADA"],
        help="Select which accessibility standards to audit against.",
    )

    st.divider()

    # About section
    st.markdown(
        """
        **About this tool**

        Built to support faculty in remediating digital course content
        under **Title II of the ADA** (28 CFR Part 35), effective
        April 24, 2024 for large public institutions.

        Version 0.1 — Development
        """
    )


# -----------------------------------------------------------------------------
# MAIN CONTENT — Two-column layout
# st.columns() creates side-by-side panels.
# col1 (left) = upload & controls; col2 (right) = results / preview
# The [1, 1] ratio means both columns are equal width.
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    # -------------------------------------------------------------------------
    # FILE UPLOAD WIDGET
    # st.file_uploader() creates a drag-and-drop upload area.
    # 'type' restricts accepted file formats.
    # The uploaded file is returned as a BytesIO-like object when present.
    # -------------------------------------------------------------------------
    st.subheader("1. Upload PDF")
    uploaded_file = st.file_uploader(
        label="Choose a PDF file",
        type=["pdf"],
        help="Upload the course PDF you want to check for accessibility issues.",
        key="uploaded_pdf",
    )

    # Show a success message and file info once a file is uploaded
    if uploaded_file is not None:
        st.success(f"File uploaded: **{uploaded_file.name}**")
        st.caption(f"Size: {uploaded_file.size / 1024:.1f} KB")

        # ---------------------------------------------------------------------
        # ACTION BUTTONS
        # Placed inside a container so they visually group together.
        # st.button() returns True only on the click that triggers a re-run.
        # ---------------------------------------------------------------------
        st.subheader("2. Run Checks")

        # Use columns to place two buttons side by side
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            run_audit = st.button(
                "🔍 Run Accessibility Audit",
                type="primary",   # Renders as a filled/highlighted button
                use_container_width=True,
            )

        with btn_col2:
            run_ocr = st.button(
                "📄 Run OCR",
                type="secondary",
                use_container_width=True,
                help="Extract text from scanned/image-based pages using Tesseract OCR.",
            )

        # ---------------------------------------------------------------------
        # PLACEHOLDER LOGIC — Audit action
        # This section will grow as we add real PDF analysis modules.
        # For now it shows a placeholder message to confirm the button works.
        # ---------------------------------------------------------------------
        if run_audit:
            with st.spinner("Analyzing PDF for accessibility issues..."):
                # TODO: Replace this block with real audit logic in Phase 2
                st.session_state["audit_run"] = True
                st.session_state["audit_file"] = uploaded_file.name

        if run_ocr:
            with st.spinner("Running OCR — this may take a moment for large files..."):
                # TODO: Replace with pytesseract / easyocr logic in Phase 2
                st.session_state["ocr_run"] = True


with col2:
    # -------------------------------------------------------------------------
    # RESULTS PANEL
    # Shows the output of the audit / OCR in the right column.
    # -------------------------------------------------------------------------
    st.subheader("3. Results")

    # Display audit results if they exist in session state
    if st.session_state.get("audit_run"):
        st.info(
            f"Audit queued for: **{st.session_state.get('audit_file', 'unknown')}**\n\n"
            "Full accessibility checks will appear here in the next development phase."
        )

        # Preview of the accessibility checklist that will be generated
        # st.expander() creates a collapsible section
        with st.expander("📋 Accessibility Checklist Preview (coming in Phase 2)", expanded=True):
            # Each item maps to a WCAG 2.1 Success Criterion
            checklist_items = [
                ("1.1.1 Non-text Content", "Alt text present for all images", "WCAG 2.1 SC 1.1.1"),
                ("1.3.1 Info & Relationships", "Document has tagged structure (headings, lists)", "WCAG 2.1 SC 1.3.1"),
                ("1.3.2 Meaningful Sequence", "Reading order is logical", "WCAG 2.1 SC 1.3.2"),
                ("1.4.3 Contrast (Minimum)", "Text color contrast ≥ 4.5:1", "WCAG 2.1 SC 1.4.3"),
                ("2.4.2 Page Titled", "PDF has a document title set", "WCAG 2.1 SC 2.4.2"),
                ("3.1.1 Language of Page", "Document language is specified (/Lang)", "WCAG 2.1 SC 3.1.1"),
                ("PDF/UA — Tagged PDF", "All content is tagged for assistive technology", "PDF/UA-1"),
            ]

            # Display as a simple table using markdown
            # In Phase 2 this will show real Pass/Fail status
            st.markdown("| Check | Description | Standard |")
            st.markdown("|-------|-------------|----------|")
            for check_id, description, standard in checklist_items:
                st.markdown(f"| {check_id} | {description} | {standard} |")

    elif st.session_state.get("ocr_run"):
        st.info("OCR will display extracted text here in the next development phase.")

    else:
        # Default state — no file or audit yet
        st.markdown(
            """
            Upload a PDF and click **Run Accessibility Audit** to see results here.

            The audit will check for:
            - 🖼️ Missing alt text on images
            - 🏷️ Missing or incorrect heading structure
            - 📖 Improper reading order
            - 🌐 Missing document language tag
            - 🔤 Scanned (image-only) pages that need OCR
            - 🎨 Insufficient color contrast
            - 📑 Missing document title metadata
            """
        )


# -----------------------------------------------------------------------------
# FOOTER
# A simple informational footer explaining the legal context.
# -----------------------------------------------------------------------------
st.divider()
st.caption(
    "This tool supports compliance with **Title II of the ADA** (28 CFR Part 35) "
    "and **WCAG 2.1 Level AA**. It provides guidance and analysis but does not "
    "constitute legal advice. Always consult your institution's accessibility office."
)
