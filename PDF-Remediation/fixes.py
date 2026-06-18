"""Accessibility fix functions."""

# -------------------------------------------------------------------------------
# fixes.py — applies in-place fixes to the working copy of the PDF
#
# Functions:
#   apply_fix_missing_title()          — write document title to metadata
#   apply_fix_missing_lang()           — write /Lang tag to PDF root
#   apply_fix_bookmarks()              — generate and write PDF outline
#   apply_fix_untagged()               — acknowledge; real fix happens at DOCX export
#   apply_fix_alt_text()               — acknowledge; alt text embedded in DOCX export
#   apply_fix_heading_hierarchy()      — acknowledge; hierarchy corrected at DOCX export
#   apply_fix_readability_barrier()    — acknowledge; font size enforced at DOCX export
#
# Dispatch table:
#   FIX_DISPATCH  — maps issue ID → fix function; used by render_resolving_issue()
# -------------------------------------------------------------------------------

import io

import fitz
import pikepdf

from analysis import _generate_toc_from_font_sizes


def apply_fix_missing_title(working_bytes, fix_data):
    """
    Write a document title to the PDF's Info dictionary and XMP metadata.

    Uses both pdf.docinfo (old-style Info dict) and pdf.open_metadata() (XMP)
    for maximum reader compatibility.

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Must contain "confirmed_title" (set by the UI after
                         faculty edits/approves) or "title_candidate" as fallback.

    Returns:
        (bytes, str): Updated PDF bytes and a short confirmation message.
    """
    title = (fix_data.get("confirmed_title") or fix_data.get("title_candidate", "")).strip()
    if not title:
        return working_bytes, "No title provided — metadata unchanged."
    try:
        with pikepdf.open(io.BytesIO(working_bytes)) as pdf:
            with pdf.open_metadata() as meta:
                meta["dc:title"] = title
            pdf.docinfo["/Title"] = title
            out = io.BytesIO()
            pdf.save(out)
            return out.getvalue(), f"Title set to \"{title}\"."
    except Exception as e:
        return working_bytes, f"Could not apply title fix: {e}"


def apply_fix_missing_lang(working_bytes, fix_data):
    """
    Write a /Lang entry to the PDF's document root.

    /Lang is the standard PDF mechanism for declaring the document language.
    Screen readers use it to select the correct speech engine and pronunciation
    rules. (WCAG 2.2 SC 3.1.1)

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Must contain "lang_code" (BCP 47, e.g. "en-US").

    Returns:
        (bytes, str): Updated PDF bytes and a short confirmation message.
    """
    lang_code = fix_data.get("lang_code", "en-US")
    try:
        with pikepdf.open(io.BytesIO(working_bytes)) as pdf:
            pdf.Root["/Lang"] = pikepdf.String(lang_code)
            out = io.BytesIO()
            pdf.save(out)
            return out.getvalue(), f"Language tag set to '{lang_code}'."
    except Exception as e:
        return working_bytes, f"Could not apply language fix: {e}"


def apply_fix_bookmarks(working_bytes, fix_data):
    """
    Generate and write a bookmark outline to the PDF using font-size heuristics
    to detect heading structure.

    Uses PyMuPDF's set_toc() which writes a proper PDF /Outline tree that PDF
    readers and assistive technology can navigate. (WCAG 2.2 SC 2.4.5)

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Unused; included for consistent function signature.

    Returns:
        (bytes, str): Updated PDF bytes and a short confirmation message.
    """
    try:
        doc = fitz.open(stream=working_bytes, filetype="pdf")
        toc = _generate_toc_from_font_sizes(doc)
        if toc:
            doc.set_toc(toc)
        out = io.BytesIO()
        doc.save(out)
        doc.close()
        count = len(toc)
        return out.getvalue(), f"Added {count} bookmark{'s' if count != 1 else ''}."
    except Exception as e:
        return working_bytes, f"Could not apply bookmarks fix: {e}"


def apply_fix_untagged(working_bytes, fix_data):
    """
    Handle the untagged PDF issue.

    True in-place PDF tagging (adding a full StructTreeRoot) requires
    reconstructing the document's entire logical structure — this is beyond
    what a runtime script can reliably do without a dedicated tagging engine
    (e.g., Adobe Acrobat Pro, axesPDF, CommonLook).

    Instead, we note the issue. When the faculty member downloads their file as
    DOCX (via render_choose_format), the build_docx_from_pdf() function applies
    font-size heuristics to produce a structured DOCX with proper heading styles.
    They can then re-export that DOCX as a properly tagged PDF from Word or
    Google Docs.

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Unused.

    Returns:
        (bytes, str): Unchanged PDF bytes and an explanatory message.
    """
    return working_bytes, (
        "Noted. When you download your file as a Word document, it will be structured "
        "with proper headings and reading order — ready to re-save as a properly tagged "
        "PDF from Word or Google Docs."
    )


def apply_fix_alt_text(working_bytes, fix_data):
    """
    Handle the missing alt text issue.

    Writing alt text directly into a PDF's structure tree requires the document
    to already have a StructTreeRoot with Figure elements — which untagged PDFs
    lack entirely. For tagged PDFs, it requires locating each Figure element and
    writing the /Alt attribute.

    For now we record the acknowledgement. The alt text descriptions collected
    during the session (stored in st.session_state) are available for inclusion
    in the DOCX output.

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Contains "images" list from analysis.

    Returns:
        (bytes, str): Unchanged PDF bytes and a confirmation message.
    """
    return working_bytes, (
        "The text descriptions you've provided will be included in the Word document output. "
        "When you re-export from Word, you can add them as alt text to each image."
    )


def apply_fix_heading_hierarchy(working_bytes, fix_data):
    """
    Handle the heading hierarchy issue.

    Rewriting the StructTreeRoot to correct heading levels requires modifying
    both the structure tree and the page content streams — this cannot be done
    reliably in-place without a dedicated tagging engine.

    The real fix manifests in the DOCX output: build_docx_from_pdf() uses
    font-size heuristics to assign correct Heading 1 / Heading 2 / Heading 3
    styles, producing a document with a valid hierarchy that the faculty member
    can re-export as a properly tagged PDF from Word or Google Docs.

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Contains "issue_type" and "heading_levels".

    Returns:
        (bytes, str): Unchanged PDF bytes and an explanatory message.
    """
    return working_bytes, (
        "Noted. The Word document output will use the correct heading structure "
        "based on your document's visual layout. Re-exporting from Word will produce "
        "a properly tagged PDF with a valid heading hierarchy."
    )


def apply_fix_readability_barrier(working_bytes, fix_data):
    """
    Handle severe and moderate readability barrier issues (font size too small).

    Like the untagged PDF and heading hierarchy fixes, this cannot be corrected
    in the original PDF bytes at runtime — changing font sizes requires
    rewriting page content streams, which is beyond safe in-place editing.

    The fix manifests in the DOCX output path: build_docx_from_pdf() enforces
    a minimum font size so all body text is at least 9pt in the Word document.
    Faculty can then re-export from Word as a properly readable PDF.

    Parameters:
        working_bytes (bytes): Current working copy of the PDF.
        fix_data (dict): Contains pct_affected, small_chars, total_chars.

    Returns:
        (bytes, str): Unchanged PDF bytes and an explanatory message.
    """
    pct = fix_data.get("pct_affected", 0)
    return working_bytes, (
        f"Noted — {pct}% of your text is below 9pt. When you download your file "
        "as a Word document, all text will be brought up to a comfortable minimum "
        "size. Re-exporting that Word file as PDF will carry the correction through."
    )


# Dispatch table: maps issue ID → fix function.
# Used by render_resolving_issue() to apply the right fix after faculty confirms.
FIX_DISPATCH = {
    "missing_title":                apply_fix_missing_title,
    "missing_lang":                 apply_fix_missing_lang,
    "missing_bookmarks":            apply_fix_bookmarks,
    "untagged_pdf":                 apply_fix_untagged,
    "missing_alt_text":             apply_fix_alt_text,
    "heading_hierarchy":            apply_fix_heading_hierarchy,
    "readability_barrier_severe":   apply_fix_readability_barrier,
    "readability_barrier_moderate": apply_fix_readability_barrier,
}
