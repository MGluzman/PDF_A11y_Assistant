"""Manual review checklist screen."""

# -------------------------------------------------------------------------------
# ui/manual_review.py — manual accessibility checklist (algorithmic blind spots)
#
# Functions:
#   render_manual_review() — 9-item checklist covering charts, video, math,
#                            color cues, links, tables, abbreviations, non-English
#                            passages, and decorative image verification
# -------------------------------------------------------------------------------

import streamlit as st

from ui.shared import (
    SEVERITY_LABELS,
    render_page_header,
    render_page_title,
    _render_go_back,
)
from images import extract_image_by_source


def render_manual_review():
    """
    Purpose: Surface accessibility issues that require human judgment.
    These are real WCAG 2.2 / Title II problems the app cannot detect
    algorithmically. Faculty review each item and mark it OK or needing attention.
    """
    ITEMS = [
        {
            "id":       "charts_graphs",
            "severity": "red",
            "title":    "Charts, graphs, and diagrams",
            "check":    "Does the alt text for each chart describe the data and key takeaway — not just the visual appearance? A description should say what the data shows and what conclusion to draw, not just 'bar chart.'",
            "guidance": "Revisit the alt text for each chart or graph. Describe the main finding or trend — your students who can't see the image should understand the point it makes, not just that a chart exists.",
        },
        {
            "id":       "video_audio",
            "severity": "red",
            "title":    "Embedded video or audio",
            "check":    "Does your document include any embedded video or audio clips? If so, do they have captions or a written transcript?",
            "guidance": "Add a written transcript or caption file to any audio or video content before sharing. Students who are deaf or hard of hearing cannot access that content without one.",
        },
        {
            "id":       "math_equations",
            "severity": "red",
            "title":    "Math and equations",
            "check":    "Are equations embedded as images, or typed as text? Even typed math notation (x², ∑, ∫) may not be read correctly by all screen readers.",
            "guidance": "For documents with significant math content, consider providing a written description of what each equation represents, or use MathType/LaTeX formatting. Image-based equations need alt text that explains their meaning, not just their appearance.",
        },
        {
            "id":       "color_only_cue",
            "severity": "yellow",
            "title":    "Color used as the only cue for meaning",
            "check":    "Does your document use color to signal something important — like red text for required items, or color-coded categories — without any other indicator like a label, symbol, or text?",
            "guidance": "Add a text label, symbol, or pattern alongside any color-coded elements. For example: 'Required *' instead of red text alone. Students who are color blind or printing in black and white will miss color-only signals entirely.",
        },
        {
            "id":       "link_text",
            "severity": "yellow",
            "title":    "Non-descriptive link text",
            "check":    "Do any links say 'click here,' 'this link,' or 'read more'? Screen readers read link text in isolation, without the surrounding sentence for context.",
            "guidance": "Edit link text to describe the destination. Instead of 'click here for the syllabus,' write 'Fall 2025 Course Syllabus.' This helps screen reader users understand where each link goes.",
        },
        {
            "id":       "table_structure",
            "severity": "yellow",
            "title":    "Table structure and headers",
            "check":    "Do your tables have proper header rows — actually marked as headers in the document, not just visually bold? Does each table still make sense when read row by row?",
            "guidance": "In your source document, mark header rows using the built-in table header option — not bold formatting. Re-export as PDF to carry the structure through. Screen readers read tables cell by cell and rely on headers to give each cell meaning.",
        },
        {
            "id":       "abbreviations",
            "severity": "green",
            "title":    "Abbreviations and acronyms",
            "check":    "Are discipline-specific abbreviations and acronyms spelled out the first time they appear?",
            "guidance": "Add a brief definition on first use (e.g., 'CUNY — City University of New York'), or include a glossary at the end of the document. This helps all readers, not just those using assistive technology.",
        },
        {
            "id":       "non_english",
            "severity": "green",
            "title":    "Non-English passages",
            "check":    "Does your document include any quotes or passages in a different language? Those sections may be read aloud with incorrect pronunciation by screen readers.",
            "guidance": "In Word: select the non-English text → Review → Language → Set Proofing Language. This tells screen readers to switch to the correct speech engine for that passage.",
        },
        {
            "id":       "decorative_images",
            "severity": "green",
            "title":    "Decorative image verification",
            "check":    "If this document had images, review any the app auto-classified as decorative or removed as scan artifacts. Was anything accidentally excluded that students need to see?",
            "guidance": "Compare the images in your original file with the output. If a content image was removed or incorrectly marked decorative, you can re-upload and work through the image workflow again.",
        },
    ]

    render_page_header()
    render_page_title("Manual review checklist")
    st.divider()

    st.markdown("### One more step — a quick manual check")
    st.markdown(
        "There are a few things I can't verify automatically. This should only take "
        "a minute — just a quick look at your document for each item below."
    )

    if "manual_review_results" not in st.session_state:
        st.session_state.manual_review_results = {}

    results = st.session_state.manual_review_results

    for item in ITEMS:
        item_id = item["id"]
        result  = results.get(item_id)

        st.divider()

        status = " ✓" if result == "ok" else " ⚠️" if result == "attention" else ""
        st.markdown(
            f"**{SEVERITY_LABELS[item['severity']]} — {item['title']}**{status}"
        )
        st.caption(item["check"])

        # Decorative image verification — show thumbnails and reinstate option
        if item_id == "decorative_images":
            alt_results = st.session_state.get("alt_text_results", {})
            alt_images  = st.session_state.get("alt_text_images", [])

            if not alt_images:
                st.caption("No images were processed in this session.")
            else:
                REMOVED_TYPES = {"artifact", "background", "edge_artifact"}
                pdf_source = (
                    st.session_state.working_pdf_bytes or st.session_state.file_bytes
                )

                decorative_imgs = [
                    img for img in alt_images
                    if alt_results.get(img["img_key"], {}).get("type") == "decorative"
                ]
                removed_imgs = [
                    img for img in alt_images
                    if alt_results.get(img["img_key"], {}).get("type") in REMOVED_TYPES
                ]

                if decorative_imgs:
                    st.markdown(
                        f"**{len(decorative_imgs)} image{'s' if len(decorative_imgs) != 1 else ''} "
                        "marked as decorative** — these will have empty alt text in the output."
                    )
                    n_cols = min(len(decorative_imgs), 4)
                    cols = st.columns(n_cols)
                    for i, img in enumerate(decorative_imgs):
                        with cols[i % n_cols]:
                            img_bytes, _ = extract_image_by_source(pdf_source, img)
                            if img_bytes:
                                pg = alt_results.get(img["img_key"], {}).get(
                                    "page", img.get("page", "?")
                                )
                                st.image(
                                    img_bytes,
                                    caption=f"Page {pg} — Decorative",
                                    use_container_width=True,
                                )

                if removed_imgs:
                    TYPE_LABELS = {
                        "artifact":      "Scan artifact",
                        "background":    "Page background",
                        "edge_artifact": "Edge artifact",
                    }
                    st.markdown(
                        f"**{len(removed_imgs)} image{'s' if len(removed_imgs) != 1 else ''} "
                        "excluded from the output** (marked as artifacts or backgrounds)."
                    )
                    for img in removed_imgs:
                        img_key = img["img_key"]
                        kind    = alt_results.get(img_key, {}).get("type", "artifact")
                        pg      = alt_results.get(img_key, {}).get(
                            "page", img.get("page", "?")
                        )
                        label   = TYPE_LABELS.get(kind, "Removed image")

                        with st.expander(f"Page {pg} — {label}", expanded=True):
                            img_bytes, _ = extract_image_by_source(pdf_source, img)
                            col_img, col_btn = st.columns([3, 1])
                            with col_img:
                                if img_bytes:
                                    st.image(img_bytes, width=200)
                            with col_btn:
                                if st.button(
                                    "Reinstate",
                                    key=f"reinstate_{img_key}",
                                    help=(
                                        "Remove the 'excluded' classification and send "
                                        "this image back through the alt text workflow."
                                    ),
                                ):
                                    new_results = dict(alt_results)
                                    new_results.pop(img_key, None)
                                    st.session_state.alt_text_results = new_results

                                    for idx, m in enumerate(alt_images):
                                        if m["img_key"] == img_key:
                                            st.session_state.alt_text_index = idx
                                            break
                                    st.session_state.alt_text_phase     = "question_1"
                                    st.session_state.alt_text_return_to = "manual_review"
                                    st.session_state.step               = "image_alt_text"
                                    st.rerun()

                if not decorative_imgs and not removed_imgs:
                    st.caption(
                        "All images were classified as informational — "
                        "nothing was marked decorative or removed."
                    )

        if result is None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Looks fine ✓",
                    key=f"mr_ok_{item_id}",
                    use_container_width=True,
                ):
                    st.session_state.manual_review_results[item_id] = "ok"
                    st.rerun()
            with col2:
                if st.button(
                    "Needs attention ⚠️",
                    key=f"mr_att_{item_id}",
                    use_container_width=True,
                ):
                    st.session_state.manual_review_results[item_id] = "attention"
                    st.rerun()

        elif result == "attention":
            st.info(item["guidance"])
            if st.button(
                "Got it — mark as reviewed",
                key=f"mr_done_{item_id}",
            ):
                st.session_state.manual_review_results[item_id] = "ok"
                st.rerun()

        # result == "ok": checkmark already shown in header, nothing else needed

    st.divider()

    reviewed = len(results)
    total    = len(ITEMS)
    if reviewed < total:
        st.caption(f"{reviewed} of {total} items reviewed")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Continue to download →",
            type="primary",
            use_container_width=True,
            key="mr_continue",
        ):
            st.session_state.step = "choose_format"
            st.rerun()
    with col2:
        if st.button(
            "Skip this step",
            use_container_width=True,
            key="mr_skip",
        ):
            st.session_state.step = "choose_format"
            st.rerun()

    _render_go_back("issue_list")
