"""Issue workflow screens."""

# -------------------------------------------------------------------------------
# ui/issues.py — issue list, fix screens, re-analysis, and continue/stop
#
# Functions:
#   render_issue_list()        — prioritized issue list grouped by severity
#   render_resolving_issue()   — per-issue fix UI with faculty confirmation
#   render_continue_or_stop()  — pause after each fix: keep going or stop?
#   render_re_analysis()       — re-analyze after every 3 resolved issues
# -------------------------------------------------------------------------------

import fitz
import streamlit as st

from ui.shared import (
    SEVERITY_LABELS,
    render_page_header,
    render_page_title,
    _render_abandon_button,
    _render_go_back,
)
from analysis import analyze_pdf, _generate_toc_from_font_sizes, _lang_display_name, _describe_heading_sequence
from fixes import FIX_DISPATCH
from docx_export import build_docx_from_pdf
from ui.images_ui import render_issue_panels, render_plan_box


def render_issue_list():
    """
    Purpose: Present all remaining issues, grouped by severity (Red → Yellow → Green).
    User clicks any issue to start resolving it in any order they choose.
    Per CLAUDE.md: display the Priority Recommendation message verbatim first.
    """
    render_page_header()
    render_page_title("Accessibility Scan Results")
    st.divider()

    remaining = [
        issue for issue in st.session_state.issues
        if issue["id"] not in st.session_state.resolved_ids
        and issue["id"] not in st.session_state.get("skipped_ids", [])
    ]

    if not remaining:
        st.session_state.step = "manual_review"
        st.rerun()
        return

    pad_l, msg_col, pad_r = st.columns([1, 4, 1])
    with msg_col:
        st.markdown(
            """
            <div style='
                background-color: #ffffff;
                border: 1px solid #882346;
                border-radius: 6px;
                padding: 14px 18px;
                color: #000000;
                font-size: 0.95rem;
                line-height: 1.5;
            '>
            Review your results below. We strongly recommend starting with the
            <strong>Red Light</strong> and <strong>Yellow Light</strong> issues first —
            these create the most significant barriers for your students and are the
            highest priority for accessibility compliance. Fixing some Red Light issues
            may also resolve other issues automatically.<br><br>
            Click on any issue label to begin the remediation process.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <h2 style='
            text-align: center;
            font-family: "Roboto", sans-serif;
            font-size: 18pt;
            font-weight: 400;
            color: #882346;
            margin: 16px 0 8px 0;
        '>
            The following issues were found in your uploaded file: {st.session_state.file_name}
        </h2>
        """,
        unsafe_allow_html=True,
    )

    col_red, col_yellow, col_green = st.columns([1, 1, 1])
    severity_cols = {"red": col_red, "yellow": col_yellow, "green": col_green}

    for severity, col in severity_cols.items():
        severity_issues = [i for i in remaining if i["severity"] == severity]
        with col:
            st.markdown(f"### {SEVERITY_LABELS[severity]}")
            if not severity_issues:
                st.caption("No issues in this category.")
                continue
            for issue in severity_issues:
                if st.button(
                    issue["title"],
                    key=f"issue_btn_{issue['id']}",
                    use_container_width=True,
                ):
                    st.session_state.current_issue_id = issue["id"]
                    st.session_state.proposed_fix = issue["fix_preview"]
                    if issue["id"] == "untagged_pdf":
                        st.session_state.step = "source_file_question"
                    elif issue["id"] == "missing_alt_text":
                        st.session_state.alt_text_images = issue.get("fix_data", {}).get("images", [])
                        st.session_state.alt_text_index = 0
                        st.session_state.alt_text_phase = "classifying"
                        st.session_state.alt_text_results = {}
                        st.session_state.alt_text_auto_classifications = {}
                        st.session_state.step = "image_alt_text"
                    else:
                        st.session_state.step = "resolving_issue"
                    st.rerun()

    total    = len(st.session_state.issues)
    resolved = len(st.session_state.resolved_ids)
    skipped  = len(st.session_state.get("skipped_ids", []))
    st.divider()
    caption = f"{resolved} of {total} issues resolved"
    if skipped:
        caption += f" · {skipped} skipped"
    st.caption(caption)

    if resolved > 0:
        if st.button(
            "Download my progress so far",
            use_container_width=True,
        ):
            st.session_state.step = "choose_format"
            st.rerun()

    _render_go_back("upload")


def render_resolving_issue():
    """
    Purpose: Show the selected issue and its proposed fix for faculty review.
    Per CLAUDE.md Per-Issue QA Process:
      Step 1 — Internal self-check (not shown to user — we simulate this).
      Step 2 — Faculty confirmation with exact verbatim message.
    When the faculty member clicks "No, let's try again.", an issue-specific
    alternative is offered before falling back to returning to the issue list.
    """
    render_page_header()
    render_page_title("Fixing an issue")
    st.divider()

    issue = next(
        (i for i in st.session_state.issues if i["id"] == st.session_state.current_issue_id),
        None,
    )

    if issue is None:
        st.session_state.step = "issue_list"
        st.rerun()
        return

    st.markdown(f"### {SEVERITY_LABELS[issue['severity']]} — {issue['title']}")
    st.markdown(f"*{issue['wcag']} | {issue['ada']}*")
    st.divider()

    render_issue_panels(issue["description"])

    st.divider()

    def _apply_and_advance():
        """Apply the fix for the current issue and advance to the next step."""
        fix_fn = FIX_DISPATCH.get(issue["id"])
        if fix_fn and st.session_state.working_pdf_bytes:
            new_bytes, _ = fix_fn(
                st.session_state.working_pdf_bytes,
                issue.get("fix_data", {}),
            )
            st.session_state.working_pdf_bytes = new_bytes
        st.session_state.resolved_ids.append(issue["id"])
        st.session_state.resolved_count      += 1
        st.session_state.current_issue_id    = None
        st.session_state.proposed_fix        = None
        st.session_state.showing_alternative = False
        if (
            st.session_state.resolved_count % 3 == 0
            and not st.session_state.reanalysis_done
        ):
            st.session_state.step = "re_analysis"
        else:
            st.session_state.reanalysis_done = False
            st.session_state.step = "continue_or_stop"
        st.rerun()

    def _skip_issue():
        """Mark the current issue as skipped and return to the issue list."""
        st.session_state.skipped_ids.append(issue["id"])
        st.session_state.current_issue_id    = None
        st.session_state.showing_alternative = False
        st.session_state.step                = "issue_list"
        st.rerun()

    def _docx_path_buttons(primary_label="Got it — apply it anyway"):
        """Two-button footer shared by every DOCX-path alternative-mode branch."""
        col1, col2 = st.columns(2)
        with col1:
            if st.button(primary_label, type="primary", use_container_width=True, key="alt_yes"):
                _apply_and_advance()
        with col2:
            if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                _skip_issue()

    # =========================================================================
    # ALTERNATIVE MODE
    # =========================================================================
    if st.session_state.get("showing_alternative", False):

        st.markdown("### Let's try a different approach")

        if issue["id"] == "missing_title":
            st.markdown(
                "No problem — the field is yours. Clear it and type any title you'd like "
                "to use for this document:"
            )
            new_title = st.text_input(
                "Document title:",
                value="",
                key="title_input_alt",
                help="Type a title from scratch — anything that describes the document.",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Save this title",
                    type="primary",
                    use_container_width=True,
                    key="alt_yes",
                ):
                    value = (new_title or "").strip()
                    if not value:
                        st.warning("Please enter a title before saving.")
                    else:
                        issue["fix_data"]["confirmed_title"] = value
                        _apply_and_advance()
            with col2:
                if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                    _skip_issue()

        elif issue["id"] == "missing_lang":
            lang_options = {
                "English (United States)": "en-US",
                "English (United Kingdom)": "en-GB",
                "Spanish":                 "es-ES",
                "French":                  "fr-FR",
                "German":                  "de-DE",
                "Portuguese":              "pt-PT",
                "Italian":                 "it-IT",
                "Chinese (Simplified)":    "zh-CN",
                "Chinese (Traditional)":   "zh-TW",
                "Japanese":                "ja",
                "Korean":                  "ko",
                "Arabic":                  "ar",
                "Russian":                 "ru",
                "Hindi":                   "hi",
                "Dutch":                   "nl-NL",
                "Polish":                  "pl",
                "Turkish":                 "tr",
            }
            current_code = issue.get("fix_data", {}).get("lang_code", "en-US")
            current_display = next(
                (k for k, v in lang_options.items() if v == current_code),
                "English (United States)",
            )
            st.markdown(
                f"The auto-detected language was **{_lang_display_name(current_code)}**. "
                "If that's not right, choose the correct language from the list below:"
            )
            selected_name = st.selectbox(
                "Document language:",
                options=list(lang_options.keys()),
                index=list(lang_options.keys()).index(current_display),
                key="lang_select_alt",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Apply this language",
                    type="primary",
                    use_container_width=True,
                    key="alt_yes",
                ):
                    issue["fix_data"]["lang_code"] = lang_options[selected_name]
                    _apply_and_advance()
            with col2:
                if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                    _skip_issue()

        elif issue["id"] == "missing_bookmarks":
            st.markdown(
                "Here's the bookmark structure I would add, based on the headings I found "
                "in your document. Take a look — if it looks right, go ahead and add them."
            )
            toc = []
            if st.session_state.working_pdf_bytes:
                try:
                    doc_preview = fitz.open(
                        stream=st.session_state.working_pdf_bytes, filetype="pdf"
                    )
                    toc = _generate_toc_from_font_sizes(doc_preview)
                    doc_preview.close()
                except Exception:
                    toc = []

            if toc:
                level_indent = {1: "", 2: "    ", 3: "        "}
                lines = [
                    f"{level_indent.get(level, '')}• **{title}** — page {page}"
                    for level, title, page in toc
                ]
                st.markdown("  \n".join(lines))
            else:
                st.warning(
                    "I wasn't able to detect any headings in your document — it may not have "
                    "a clear heading structure, so no bookmarks can be generated automatically. "
                    "You can skip this issue or add headings to your source document and re-upload."
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Add these bookmarks",
                    type="primary",
                    use_container_width=True,
                    key="alt_yes",
                    disabled=(not toc),
                ):
                    _apply_and_advance()
            with col2:
                if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                    _skip_issue()

        elif issue["id"] == "untagged_pdf":
            st.info(
                "An untagged PDF can't be fully fixed by editing the PDF directly — adding "
                "a proper structure tree requires specialized software like Adobe Acrobat Pro. "
                "Instead, this tool converts your document to a Word file (.docx) with real "
                "heading styles, list formatting, and reading order built in. You can then "
                "re-export that Word file as a properly tagged PDF from Word or Google Docs.\n\n"
                "If you download your file as a Word document at the end of this session, "
                "the structural improvements will be included automatically."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Got it — apply it anyway",
                    type="primary",
                    use_container_width=True,
                    key="alt_yes",
                ):
                    _apply_and_advance()
            with col2:
                if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                    _skip_issue()

        elif issue["id"] == "heading_hierarchy":
            fix_data   = issue.get("fix_data", {})
            issue_type = fix_data.get("issue_type", "skip")
            if issue_type == "skip":
                st.info(
                    "This fix uses font sizes to infer which lines are headings and what level "
                    "each should be, then rewrites the heading tags so they follow a logical "
                    "sequence (Heading 1 → Heading 2 → Heading 3) with no skipped levels.\n\n"
                    "This works well for most documents, but it relies on consistent font sizing "
                    "for headings — so if your document uses unusual formatting, the result may "
                    "not be perfect. You can always review the output before finalizing."
                )
            else:
                st.info(
                    "This fix corrects the heading structure so it follows a logical sequence. "
                    "Screen reader users rely on headings to navigate — without a consistent "
                    "hierarchy, they can't tell which sections are major and which are sub-sections."
                )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Got it — apply it anyway",
                    type="primary",
                    use_container_width=True,
                    key="alt_yes",
                ):
                    _apply_and_advance()
            with col2:
                if st.button("Skip this issue for now", use_container_width=True, key="alt_skip"):
                    _skip_issue()

        elif issue["id"] in ("readability_barrier_severe", "readability_barrier_moderate"):
            pct = issue.get("fix_data", {}).get("pct_affected", 0)
            st.info(
                f"About {pct}% of your document's text is below 9pt. This fix works "
                "by enforcing a minimum font size when you export to Word (.docx) — "
                "the original PDF is left unchanged, but the Word version will have "
                "all text at a comfortably readable size.\n\n"
                "If you re-export that Word file as a PDF, the corrected sizes carry "
                "through automatically."
            )
            _docx_path_buttons()

        elif issue["id"] == "reading_order":
            st.info(
                "This fix works through the Word document export. When your PDF is "
                "converted to a Word document, content is extracted and re-laid-out in "
                "a visual top-to-bottom sequence — which corrects cases where the PDF's "
                "internal block order doesn't match the expected reading flow.\n\n"
                "Re-exporting that Word file as PDF will produce a document with a "
                "correct, consistent reading order."
            )
            _docx_path_buttons()

        elif issue["id"] == "inconsistent_list_tagging":
            st.info(
                "This fix is handled through the Word document export. When your PDF "
                "is converted to a Word document, lines formatted with bullets, dashes, "
                "or numbers are recognized and converted to properly structured list "
                "elements with correct indentation and tags.\n\n"
                "Re-exporting the Word file as PDF will carry the list structure into "
                "the accessible PDF."
            )
            _docx_path_buttons()

        elif issue["id"] == "line_spacing_tight":
            tight_pct = issue.get("fix_data", {}).get("tight_pct", 0)
            st.info(
                f"About {tight_pct}% of your text has line spacing tighter than the "
                "recommended minimum. This fix applies 1.5× line spacing to body text "
                "in the Word document export — the original PDF is left unchanged.\n\n"
                "Re-exporting the Word file as PDF will carry the improved spacing "
                "through automatically."
            )
            _docx_path_buttons()

        elif issue["id"] == "letter_spacing_tight":
            st.info(
                "This fix normalizes letter spacing in the Word document export. When "
                "compressed character tracking is detected, the Word output uses each "
                "font's standard tracking — removing any artificial compression.\n\n"
                "Note: this check uses a geometric estimate and may occasionally flag "
                "documents with naturally narrow typefaces. Review the output to "
                "confirm the result looks right before finalizing."
            )
            _docx_path_buttons()

        elif issue["id"] == "excessive_text_colors":
            color_count = issue.get("fix_data", {}).get("color_count", 0)
            st.info(
                f"This document uses {color_count} distinct text colors. In the Word "
                "document export, text colors will be reduced to a small intentional "
                "set — body text and headings — removing visual noise without changing "
                "the document's content or structure.\n\n"
                "The original PDF is left unchanged. The simplified color palette only "
                "applies to the downloaded Word file."
            )
            _docx_path_buttons()

        else:
            st.info(
                "This fix is applied automatically based on what we detected in your document. "
                "If you're not sure about it, you can skip this issue for now and come back later."
            )
            _docx_path_buttons("Apply it anyway")

        _render_abandon_button()
        return

    # =========================================================================
    # STANDARD MODE
    # =========================================================================

    if issue["id"] == "missing_title":
        fix_data      = issue.get("fix_data", {})
        candidate     = fix_data.get("title_candidate", "")
        st.markdown("**Review and confirm the document title:**")
        st.markdown(issue["fix_preview"])
        confirmed_title = st.text_input(
            "Document title:",
            value=candidate,
            key="title_input",
            help="Edit this if the detected title isn't quite right, or type one from scratch.",
        )

    elif issue["id"] == "heading_hierarchy":
        confirmed_title = None
        fix_data    = issue.get("fix_data", {})
        issue_type  = fix_data.get("issue_type", "skip")
        heading_levels = fix_data.get("heading_levels", [])

        render_plan_box(issue["fix_preview"])

        if issue_type == "skip" and heading_levels:
            st.markdown("**Detected heading sequence** (problems marked in bold):")
            st.markdown(_describe_heading_sequence(heading_levels))

    elif issue["id"] == "untagged_pdf":
        render_plan_box(
            "<strong>What we'll do:</strong> Convert this document to a Word file (.docx) "
            "with your text content extracted. Because this PDF has no accessibility tags, "
            "the Word file won't have heading structure yet — <strong>you'll need to apply "
            "heading styles, set the correct reading order, and add structure</strong> in "
            "Word or Google Docs before re-saving as a PDF.<br><br>"
            "<strong>Why Word?</strong> Adding accessibility tags directly to a PDF requires "
            "specialized tools like Adobe Acrobat Pro. Word and Google Docs have built-in "
            "heading styles and structure tools that are much easier to work with — and "
            "re-saving from Word produces a properly tagged, accessible PDF.<br><br>"
            "<strong>Tip:</strong> Use Word's built-in Accessibility Checker "
            "(Review → Check Accessibility) as you work. For a step-by-step guide, see the "
            "<a href='https://guides.cuny.edu/accessibility/microsoft_word' target='_blank'>"
            "CUNY Making Word Documents Accessible</a> guide."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, let's do it.",
                type="primary",
                use_container_width=True,
                key="confirm_yes",
            ):
                st.session_state.untagged_pdf_pending = True
                st.session_state.current_issue_id    = None
                st.session_state.showing_alternative = False
                st.session_state.step                = "choose_format"
                st.rerun()
        with col2:
            if st.button(
                "No, not now.",
                use_container_width=True,
                key="confirm_no",
            ):
                st.session_state.current_issue_id    = None
                st.session_state.showing_alternative = False
                st.session_state.step                = "issue_list"
                st.rerun()

        _render_abandon_button()
        return

    elif issue["id"] == "missing_lang":
        lang_code = issue.get("fix_data", {}).get("lang_code", "en-US")
        lang_options = {
            "English (United States)": "en-US",
            "English (United Kingdom)": "en-GB",
            "Spanish":                 "es-ES",
            "French":                  "fr-FR",
            "German":                  "de-DE",
            "Portuguese":              "pt-PT",
            "Italian":                 "it-IT",
            "Chinese (Simplified)":    "zh-CN",
            "Chinese (Traditional)":   "zh-TW",
            "Japanese":                "ja",
            "Korean":                  "ko",
            "Arabic":                  "ar",
            "Russian":                 "ru",
            "Hindi":                   "hi",
            "Dutch":                   "nl-NL",
            "Polish":                  "pl",
            "Turkish":                 "tr",
        }
        current_display = next(
            (k for k, v in lang_options.items() if v == lang_code),
            "English (United States)",
        )

        st.info(
            f"**What we'll do:** Add the language tag **{_lang_display_name(lang_code)}** "
            f"(`{lang_code}`) to your document's metadata.\n\n"
            "**Why it matters:** Screen readers use the language tag to choose the right "
            "pronunciation rules and speech engine. Without it, text may be read aloud "
            "in the wrong accent or with incorrect pronunciation — especially noticeable "
            "for technical terms, proper names, and any non-English content."
        )

        st.markdown(
            f"I detected **{_lang_display_name(lang_code)}** based on your document's content. "
            "If that's not right, choose the correct language below before confirming:"
        )
        selected_name = st.selectbox(
            "Document language:",
            options=list(lang_options.keys()),
            index=list(lang_options.keys()).index(current_display),
            key="lang_select_standard",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, let's do it.",
                type="primary",
                use_container_width=True,
                key="confirm_yes",
            ):
                issue["fix_data"]["lang_code"] = lang_options[selected_name]
                _apply_and_advance()
        with col2:
            if st.button(
                "No, not now.",
                use_container_width=True,
                key="confirm_no",
            ):
                _skip_issue()

        _render_abandon_button()
        return

    elif issue["id"] == "color_only_cue":
        color_count = issue.get("fix_data", {}).get("color_count", 0)
        file_stem = (st.session_state.file_name or "document").rsplit(".", 1)[0]

        st.markdown("**Colored text detected in your document**")
        st.markdown(
            f"This document uses **{color_count} distinct text colors**. "
            "Color can create accessibility barriers in a few ways — most of which "
            "require a quick manual check rather than an automated fix. "
            "Here's what to look for:"
        )
        st.markdown(
            "**1. Color as the only cue for meaning** (WCAG 2.2 SC 1.4.1)  \n"
            "If color is the only thing distinguishing categories, required items, "
            "or warnings — with no label, symbol, or text alongside it — students "
            "who are color-blind or printing in black and white will miss that "
            "meaning entirely.  \n"
            "*Fix:* Add a text label, asterisk, or symbol next to anything communicated "
            "by color alone. For example: \"Required \\*\" instead of red text alone.\n\n"
            "**2. Text contrast** (WCAG 2.2 SC 1.4.3)  \n"
            "Colored text may not meet the minimum contrast ratio against the page "
            "background — especially light colors on white.  \n"
            "*Fix:* Check that colored text meets at least 4.5:1 contrast for body "
            "text, or 3:1 for large text (18pt+). Tools like the WebAIM Contrast "
            "Checker can help."
        )

        st.divider()
        st.markdown(
            "**To make these fixes yourself:** Download your document as a Word file, "
            "open it in Microsoft Word or Google Docs, and make the color adjustments "
            "there. The Word file already has your headings, paragraphs, and structure "
            "preserved — it's ready to edit."
        )

        if not st.session_state.get("edited_docx_bytes"):
            with st.spinner("Preparing your Word document..."):
                pdf_bytes = st.session_state.working_pdf_bytes or st.session_state.file_bytes
                st.session_state.edited_docx_bytes = build_docx_from_pdf(pdf_bytes)
        docx_bytes = st.session_state.edited_docx_bytes

        if docx_bytes:
            st.download_button(
                label="⬇ Download as Word document (.docx)",
                data=docx_bytes,
                file_name=f"{file_stem}_edited.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="color_docx_download",
            )

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "I've handled it — move on.",
                type="primary",
                use_container_width=True,
                key="confirm_yes",
            ):
                _apply_and_advance()
        with col2:
            if st.button(
                "No, not now.",
                use_container_width=True,
                key="confirm_no",
            ):
                _skip_issue()

        _render_abandon_button()
        return

    else:
        render_plan_box(issue["fix_preview"])
        confirmed_title = None

    # Faculty confirmation — exactly two choices per CLAUDE.md
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, that looks good.",
            type="primary",
            use_container_width=True,
            key="confirm_yes",
        ):
            proceed = True
            if issue["id"] == "missing_title":
                value = (confirmed_title or "").strip()
                if not value:
                    st.warning("Please enter a title before saving.")
                    proceed = False
                else:
                    issue["fix_data"]["confirmed_title"] = value

            if proceed:
                _apply_and_advance()

    with col2:
        if st.button(
            "No, let's try again.",
            use_container_width=True,
            key="confirm_no",
        ):
            st.session_state.showing_alternative = True
            st.rerun()

    _render_abandon_button()


def render_continue_or_stop():
    """
    Purpose: Give the user a natural pause after each resolved issue.
    Per CLAUDE.md: ask "keep going?" after every issue.
    """
    render_page_header()
    render_page_title("Keep going?")
    st.divider()

    resolved  = len(st.session_state.resolved_ids)
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
                st.session_state.step = "manual_review"
                st.rerun()

        st.divider()
        if st.button(
            "Download what I have so far",
            use_container_width=True,
        ):
            st.session_state.step = "choose_format"
            st.rerun()
        st.caption(
            "Saves a copy of your progress without stopping. "
            "Use the Abandon button on the download screen to come back and keep working."
        )
    else:
        st.markdown("You've worked through all the issues — great job!")
        if st.button("Continue to download", type="primary"):
            st.session_state.step = "manual_review"
            st.rerun()

    _render_abandon_button()


def render_re_analysis():
    """
    Purpose: Offer to re-analyze the document after every 3 resolved issues.
    Per CLAUDE.md: verbatim message and exactly two choices.
    """
    render_page_header()
    render_page_title("Re-checking your document")
    st.divider()

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
            with st.spinner("Re-analyzing your document..."):
                reanalysis_bytes = (
                    st.session_state.working_pdf_bytes or st.session_state.file_bytes
                )
                result = analyze_pdf(reanalysis_bytes)
                if result["status"] == "issues_found":
                    fresh_issues = [
                        i for i in result["issues"]
                        if i["id"] not in st.session_state.resolved_ids
                    ]
                    st.session_state.issues = (
                        fresh_issues
                        + [
                            i for i in st.session_state.issues
                            if i["id"] in st.session_state.resolved_ids
                        ]
                    )
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

    _render_abandon_button()
