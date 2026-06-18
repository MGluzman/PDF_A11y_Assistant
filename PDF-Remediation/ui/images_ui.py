"""Image alt text workflow screens."""

# -------------------------------------------------------------------------------
# ui/images_ui.py — image alt text workflow and shared issue panel helpers
#
# Functions:
#   render_image_alt_text()       — full per-image classification workflow
#   render_source_file_question() — intercept before untagged PDF fix
#   render_cuny_resources()       — CUNY accessibility guides for source-file path
#   render_issue_panels()         — why-box / plan-box side-by-side layout helper
#   render_plan_box()             — standalone plan box (used by issues.py)
# -------------------------------------------------------------------------------

import html as _html

import streamlit as st

from ui.shared import (
    SEVERITY_LABELS,
    render_page_header,
    render_page_title,
    _render_abandon_button,
    _render_image_nav_buttons,
    _advance_alt_text_image,
    init_state,
)
from images import (
    auto_classify_image,
    run_auto_classification,
    extract_image_by_source,
    render_page_with_image_highlight,
)


def render_image_alt_text():
    """
    Purpose: Walk the faculty member through each image one at a time,
    collecting a decision (decorative vs. informational) and a text description
    for each non-decorative image.

    Per CLAUDE.md: severity is reassigned based on the faculty member's answers —
    never apply a description without their explicit confirmation.
    """
    render_page_header()
    render_page_title("Image descriptions")
    st.divider()

    images  = st.session_state.alt_text_images
    index   = st.session_state.alt_text_index
    phase   = st.session_state.alt_text_phase
    total   = len(images)
    results = st.session_state.alt_text_results
    auto_classifications = st.session_state.get("alt_text_auto_classifications", {})

    HIGH_CONFIDENCE = 0.75

    # -------------------------------------------------------------------------
    # CLASSIFYING PHASE — run auto-classification on all images (transient)
    # -------------------------------------------------------------------------
    if phase == "classifying":
        pdf_source = st.session_state.working_pdf_bytes or st.session_state.file_bytes
        with st.spinner(
            f"Reviewing {total} image{'s' if total != 1 else ''} — "
            "checking for backgrounds and scan artifacts..."
        ):
            classifications = run_auto_classification(images, pdf_source)
        st.session_state.alt_text_auto_classifications = classifications

        flagged = [
            img_key for img_key, r in classifications.items()
            if r["classification"] != "content" and r["confidence"] >= HIGH_CONFIDENCE
        ]
        if flagged:
            st.session_state.alt_text_phase = "bulk_review"
        else:
            st.session_state.alt_text_phase = "question_1"
        st.rerun()
        return

    # -------------------------------------------------------------------------
    # BULK REVIEW PHASE — one-click removal of high-confidence detections
    # -------------------------------------------------------------------------
    if phase == "bulk_review":
        flagged_images = [
            img for img in images
            if auto_classifications.get(img["img_key"], {}).get("classification") != "content"
            and auto_classifications.get(img["img_key"], {}).get("confidence", 0) >= HIGH_CONFIDENCE
        ]

        n = len(flagged_images)
        bg_count  = sum(1 for img in flagged_images
                        if auto_classifications[img["img_key"]]["classification"] == "background")
        ea_count  = sum(1 for img in flagged_images
                        if auto_classifications[img["img_key"]]["classification"] == "edge_artifact")
        art_count = sum(1 for img in flagged_images
                        if auto_classifications[img["img_key"]]["classification"] == "artifact")

        found_parts = []
        if bg_count:
            found_parts.append(f"{bg_count} page background{'s' if bg_count != 1 else ''}")
        if ea_count:
            found_parts.append(f"{ea_count} edge artifact{'s' if ea_count != 1 else ''}")
        if art_count:
            found_parts.append(f"{art_count} scan artifact{'s' if art_count != 1 else ''}")

        st.markdown("### I reviewed your images automatically")
        st.info(
            f"I found **{', '.join(found_parts)}** that look like they should be removed "
            f"rather than described. Here's what I spotted:"
        )

        pdf_source = st.session_state.working_pdf_bytes or st.session_state.file_bytes

        cols = st.columns(3)
        for i, img_meta in enumerate(flagged_images):
            img_key   = img_meta["img_key"]
            clf       = auto_classifications[img_key]
            label_map = {
                "background":    "Page background",
                "edge_artifact": "Edge artifact",
                "artifact":      "Scan artifact",
            }
            label = label_map.get(clf["classification"], clf["classification"])
            with cols[i % 3]:
                img_bytes, _ = extract_image_by_source(pdf_source, img_meta)
                if img_bytes:
                    st.image(img_bytes, use_container_width=True)
                st.caption(f"**{label}** — page {img_meta['page']}")
                st.caption(clf["reason"])

        st.divider()
        st.markdown("**What would you like to do?**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                f"Remove all {n} flagged items",
                type="primary",
                use_container_width=True,
                key="bulk_remove_all",
            ):
                for img_meta in flagged_images:
                    img_key = img_meta["img_key"]
                    clf     = auto_classifications[img_key]
                    results[img_key] = {
                        "type":     clf["classification"],
                        "severity": "green",
                        "alt_text": "",
                        "page":     img_meta["page"],
                    }
                st.session_state.alt_text_results = results
                first_idx = next(
                    (i for i, img in enumerate(images) if img["img_key"] not in results),
                    None,
                )
                if first_idx is not None:
                    st.session_state.alt_text_index = first_idx
                    st.session_state.alt_text_phase = "question_1"
                else:
                    st.session_state.alt_text_phase = "summary"
                st.rerun()

        with col2:
            if st.button(
                "Let me review each one individually",
                use_container_width=True,
                key="bulk_review_each",
            ):
                st.session_state.alt_text_phase = "question_1"
                st.rerun()

        _render_abandon_button()
        return

    # -------------------------------------------------------------------------
    # SUMMARY PHASE — shown after all images have been processed
    # -------------------------------------------------------------------------
    if phase == "summary":
        st.markdown("### Review your image decisions")
        st.markdown(
            "Here's what we have for each image. Confirm to apply all decisions, "
            "or go back to make changes."
        )
        st.divider()

        REMOVED_TYPES = ("artifact", "background", "edge_artifact")
        removed = [img for img in images
                   if results.get(img["img_key"], {}).get("type") in REMOVED_TYPES]
        skipped = [img for img in images
                   if results.get(img["img_key"], {}).get("type") == "skipped"
                   or img["img_key"] not in results]
        others  = [img for img in images
                   if results.get(img["img_key"], {}).get("type") not in REMOVED_TYPES
                   and results.get(img["img_key"], {}).get("type") not in (None, "skipped")]

        pdf_source = st.session_state.working_pdf_bytes or st.session_state.file_bytes

        if removed:
            type_label_map = {
                "artifact":      "Scan artifact",
                "background":    "Page background",
                "edge_artifact": "Edge artifact",
            }
            st.warning(
                f"**{len(removed)} image{'s' if len(removed) != 1 else ''} will be "
                "excluded from the accessible output.**"
            )
            for img in removed:
                img_key = img["img_key"]
                pg      = results.get(img_key, {}).get("page", img.get("page", "?"))
                kind    = results.get(img_key, {}).get("type", "artifact")
                label   = type_label_map.get(kind, "Removed image")
                with st.expander(f"Page {pg} — {label} (will be excluded)", expanded=False):
                    img_bytes, _ = extract_image_by_source(pdf_source, img)
                    if img_bytes:
                        st.image(img_bytes, width=300)
                    st.info("This image will be excluded from the Word document output.")
            st.divider()

        if skipped:
            st.error(
                f"**{len(skipped)} image{'s' if len(skipped) != 1 else ''} "
                f"{'were' if len(skipped) != 1 else 'was'} skipped or not reviewed.** "
                "You can confirm anyway or go back to classify them."
            )
            for img in skipped:
                pg = img.get("page", "?")
                with st.expander(f"Page {pg} — Not classified", expanded=False):
                    img_bytes, _ = extract_image_by_source(pdf_source, img)
                    if img_bytes:
                        st.image(img_bytes, width=300)
                    st.caption("No decision was made for this image.")
            st.divider()

        for img in others:
            img_key = img["img_key"]
            result  = results.get(img_key, {})
            pg      = result.get("page", img.get("page", "?"))
            sev     = result.get("severity", "")
            label   = SEVERITY_LABELS.get(sev, "")
            kind    = result.get("type", "")
            alt     = result.get("alt_text", "")

            header = f"Page {pg} — {label}"
            with st.expander(header, expanded=False):
                img_bytes, _ = extract_image_by_source(pdf_source, img)
                if img_bytes:
                    st.image(img_bytes, width=300)

                if kind == "decorative":
                    st.success("Marked as decorative — no description needed.")
                else:
                    st.markdown(f"**Description:** {alt}")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, that looks good.",
                type="primary",
                use_container_width=True,
                key="alt_confirm",
            ):
                if "missing_alt_text" not in st.session_state.resolved_ids:
                    st.session_state.resolved_ids.append("missing_alt_text")
                    st.session_state.resolved_count += 1

                return_to = st.session_state.get("alt_text_return_to")
                if return_to:
                    del st.session_state["alt_text_return_to"]
                    st.session_state.step = return_to
                elif (
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
                "No, let me go back and edit.",
                use_container_width=True,
                key="alt_redo",
            ):
                st.session_state.alt_text_index = 0
                st.session_state.alt_text_phase = "question_1"
                st.rerun()
        _render_abandon_button()
        return

    # -------------------------------------------------------------------------
    # Safety net — if index is out of range, jump to summary
    # -------------------------------------------------------------------------
    if index >= total:
        st.session_state.alt_text_phase = "summary"
        st.rerun()
        return

    # -------------------------------------------------------------------------
    # PER-IMAGE HEADER — progress indicator and image previews
    # -------------------------------------------------------------------------
    current  = images[index]
    img_key  = current["img_key"]
    page_num = current["page"] - 1  # convert 1-based page number to 0-based index

    st.markdown(f"**Image {index + 1} of {total}** — found on page {current['page']}")
    st.progress(index / total)
    st.divider()

    pdf_source = st.session_state.working_pdf_bytes or st.session_state.file_bytes

    # Panel 1: full page with red highlight around the target image
    if current.get("source") == "docling":
        page_view = render_page_with_image_highlight(
            pdf_source, page_num, bbox=current.get("bbox")
        )
    else:
        page_view = render_page_with_image_highlight(
            pdf_source, page_num, xref=current.get("xref")
        )
    if page_view:
        st.caption("📍 The image being assessed is highlighted in red:")
        st.image(page_view, use_container_width=True)
    st.divider()

    # Panel 2: extracted crop at fixed width
    img_bytes, _ = extract_image_by_source(pdf_source, current)
    if img_bytes:
        st.caption("🖼 Extracted image:")
        st.image(img_bytes, width=500)

        with st.expander("🔍 View full size", expanded=False):
            st.image(img_bytes, use_container_width=True)
    elif not page_view:
        st.caption("_(Image preview unavailable for this item)_")

    st.divider()

    # -------------------------------------------------------------------------
    # QUESTION 1 — Classify the image: decorative, artifact, or informational?
    # -------------------------------------------------------------------------
    if phase == "question_1":
        COMPLETE_TYPES = {"decorative", "artifact", "background", "edge_artifact",
                          "informational"}
        existing_result = results.get(img_key, {})
        if existing_result.get("type") in COMPLETE_TYPES:
            kind = existing_result["type"]
            alt  = existing_result.get("alt_text", "")
            label_map = {
                "decorative":    "Decorative — no description needed",
                "artifact":      "Scan artifact — will be excluded from output",
                "background":    "Page background — will be excluded from output",
                "edge_artifact": "Edge artifact — will be excluded from output",
                "informational": f"Informational — description saved: \"{alt}\"",
            }
            st.success(f"✓ Already classified: **{label_map.get(kind, kind)}**")
            st.markdown(
                "You already made a decision for this image. "
                "You can keep it and move on, or change it."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Keep this — move on",
                    type="primary",
                    use_container_width=True,
                    key=f"q1_keep_{index}",
                ):
                    _advance_alt_text_image()
            with col2:
                if st.button(
                    "Change it",
                    use_container_width=True,
                    key=f"q1_change_{index}",
                ):
                    results.pop(img_key, None)
                    st.session_state.alt_text_results = results
                    st.rerun()
            _render_image_nav_buttons(index, total, img_key, current, results)
            _render_abandon_button()
            return

        # Auto-classification suggestion badge for low-confidence non-content detections
        clf = auto_classifications.get(img_key, {})
        if clf.get("classification") and clf["classification"] != "content":
            label_map = {
                "background":    "a page background",
                "edge_artifact": "a scan edge artifact",
                "artifact":      "a scan artifact",
            }
            suggestion = label_map.get(clf["classification"], clf["classification"])
            conf_pct   = int(clf.get("confidence", 0) * 100)
            st.warning(
                f"⚠️ **I think this might be {suggestion}** ({conf_pct}% confidence). "
                f"Reason: {clf.get('reason', '')}  \n"
                "You can accept my suggestion by choosing the matching option below, "
                "or override it if I got it wrong."
            )

        st.markdown("### What is this image?")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Decorative**")
            st.caption(
                "Exists only for visual appeal — a border, texture, or stock photo "
                "with no connection to the topic. No description needed."
            )
            if st.button(
                "It's decorative",
                type="primary",
                use_container_width=True,
                key=f"q1_decorative_{index}",
            ):
                results[img_key] = {
                    "type":     "decorative",
                    "severity": "green",
                    "alt_text": "",
                    "page":     current["page"],
                }
                st.session_state.alt_text_results = results
                st.toast(
                    f"Image {index + 1} marked as decorative — "
                    "empty alt text will be applied in the output.",
                    icon="✅",
                )
                _advance_alt_text_image()

        with col2:
            st.markdown("**Scan artifact**")
            st.caption(
                "A smudge, shadow, dark edge, or other visual noise from scanning. "
                "Will be excluded from the accessible output."
            )
            if st.button(
                "It's a scan artifact — remove it",
                use_container_width=True,
                key=f"q1_artifact_{index}",
            ):
                results[img_key] = {
                    "type":     "artifact",
                    "severity": "green",
                    "alt_text": "",
                    "page":     current["page"],
                }
                st.session_state.alt_text_results = results
                _advance_alt_text_image()

        with col3:
            st.markdown("**Informational**")
            st.caption(
                "Carries content students need — a chart, diagram, photo, figure, "
                "or any image that isn't purely decorative. Needs a description."
            )
            if st.button(
                "It carries information",
                use_container_width=True,
                key=f"q1_info_{index}",
            ):
                results[img_key] = {
                    "type":     "informational",
                    "severity": "yellow",
                    "alt_text": "",
                    "page":     current["page"],
                }
                st.session_state.alt_text_results = results
                st.session_state.alt_text_phase = "enter_text"
                st.rerun()

        _render_image_nav_buttons(index, total, img_key, current, results)
        _render_abandon_button()

    # -------------------------------------------------------------------------
    # ENTER TEXT — write the alt text description
    # -------------------------------------------------------------------------
    elif phase == "enter_text":
        result   = results.get(img_key, {})
        existing = result.get("alt_text", "")

        st.markdown("### Describe this image")
        st.markdown(
            "Write a description that tells students what this image shows and why it "
            "matters in the context of the document. A student who cannot see the image "
            "should be able to understand what it conveys from your description."
        )

        new_text = st.text_area(
            "Text description (alt text):",
            value=existing,
            height=120,
            key=f"alt_input_{index}",
            placeholder="Describe the image here...",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Save this description.",
                type="primary",
                use_container_width=True,
                key=f"alt_save_{index}",
            ):
                widget_key = f"alt_input_{index}"
                text = new_text.strip() or st.session_state.get(widget_key, "").strip()
                if text:
                    if img_key not in results:
                        results[img_key] = {
                            "type":     "informational",
                            "severity": "yellow",
                            "alt_text": text,
                            "page":     current["page"],
                        }
                    else:
                        results[img_key]["alt_text"] = text
                    st.session_state.alt_text_results = results
                    _advance_alt_text_image()
                else:
                    st.warning("Please enter a description before saving.")

        with col2:
            if st.button(
                "← Back to classification",
                use_container_width=True,
                key=f"alt_back_{index}",
            ):
                results.pop(img_key, None)
                st.session_state.alt_text_results = results
                st.session_state.alt_text_phase = "question_1"
                st.rerun()

        _render_image_nav_buttons(index, total, img_key, current, results)
        _render_abandon_button()


def render_source_file_question():
    """
    Purpose: Before tackling an untagged PDF, find out whether the faculty
    member has the original source file. Working from the source is always
    the more reliable path — we want to route them there when possible.
    """
    render_page_header()
    render_page_title("Before we fix this issue")
    st.divider()

    st.markdown("### Before we dig in — a quick question.")
    st.markdown(
        "The most reliable fix for an untagged PDF is to update the **original "
        "source file** directly. We're building a dedicated tool to help you do "
        "that — but in the meantime, great resources are available."
    )
    st.markdown(
        "Do you still have the original **Word, Google Docs, PowerPoint, or "
        "Google Slides** file you used to create this PDF?"
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes, I have the original file.",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.step = "cuny_resources"
            st.rerun()
    with col2:
        if st.button(
            "No, I only have the PDF.",
            use_container_width=True,
        ):
            st.session_state.step = "resolving_issue"
            st.rerun()

    _render_abandon_button()


def render_cuny_resources():
    """
    Purpose: Give faculty members who have their original source file the
    CUNY accessibility resources they need to fix it properly, then let them
    choose whether to work on that file now or continue remediating the PDF.
    """
    render_page_header()
    render_page_title("Accessibility resources")
    st.divider()

    st.markdown(
        "Working from your original source file will give you the best result — "
        "Word, Google Docs, and PowerPoint all export properly tagged, accessible "
        "PDFs when the source file is set up correctly."
    )

    st.info(
        "We're building a source-file editor directly into this tool. "
        "While that's in progress, CUNY's accessibility guides walk you through "
        "the process step by step."
    )

    st.markdown("### CUNY Accessibility Resources")
    st.markdown(
        """
        - 📚 [**CUNY Accessibility Toolkit**](https://guides.cuny.edu/accessibility)
          — Overview of accessibility standards and tools across file formats

        - 📝 [**Making Word Documents Accessible**](https://guides.cuny.edu/accessibility/microsoft_word)
          — Step-by-step guide for heading styles, alt text, reading order, and more in Word

        - 📊 [**Making PowerPoint Presentations Accessible**](https://guides.cuny.edu/accessibility/powerpoint)
          — Step-by-step guide for slide titles, alt text, reading order, and more in PowerPoint
        """
    )

    st.markdown(
        "_If your file is a **Google Doc or Google Slides** presentation, "
        "open it, go to **File → Download**, choose **Microsoft Word (.docx)** "
        "or **Microsoft PowerPoint (.pptx)**, then follow the Word or PowerPoint "
        "guide above._"
    )

    st.divider()

    st.markdown("**What would you like to do next?**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Review these resources and update my original file.",
            type="primary",
            use_container_width=True,
        ):
            if "untagged_pdf" not in st.session_state.resolved_ids:
                st.session_state.resolved_ids.append("untagged_pdf")
                st.session_state.resolved_count += 1
            st.session_state.current_issue_id = None
            st.session_state.step = "issue_list"
            st.rerun()
    with col2:
        if st.button(
            "Keep going with this PDF.",
            use_container_width=True,
        ):
            st.session_state.step = "resolving_issue"
            st.rerun()

    _render_abandon_button()


def render_issue_panels(why_text, plan_text=None):
    """
    Renders the why and plan sections side by side in styled boxes.
    Both boxes share equal width. plan_text accepts plain text or basic HTML.
    If plan_text is None, only the why-box is rendered (full width).
    """
    why_html = f"""
        <div class='issue-box-wrapper'>
            <div class='issue-why-box'>
                <div class='issue-box-label'>Why this matters for your students</div>
                {_html.escape(why_text).replace(chr(10), '<br>')}
            </div>
        </div>
    """

    if plan_text is not None:
        col_why, col_plan = st.columns(2)
        with col_why:
            st.markdown(why_html, unsafe_allow_html=True)
        with col_plan:
            st.markdown(
                f"<div class='issue-box-wrapper'>"
                f"<div class='issue-plan-box'>"
                f"<div class='issue-box-label'>Here's the plan</div>"
                f"{plan_text}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(why_html, unsafe_allow_html=True)


def render_plan_box(content_html):
    """
    Renders just the plan box (used when why-box was already rendered above
    and the plan section stands alone below it).
    content_html should be pre-formatted HTML.
    """
    st.markdown(
        f"<div class='issue-box-wrapper'>"
        f"<div class='issue-plan-box'>"
        f"<div class='issue-box-label'>Here's the plan</div>"
        f"{content_html}</div></div>",
        unsafe_allow_html=True,
    )
