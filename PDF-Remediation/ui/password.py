"""Password protection screens."""

# -------------------------------------------------------------------------------
# ui/password.py — password protection detection and walkthrough screens
#
# Functions:
#   render_password_protected()   — security warning and two-choice prompt
#   render_password_walkthrough() — step-by-step removal instructions
# -------------------------------------------------------------------------------

import streamlit as st

from ui.shared import render_page_header, render_page_title, _render_go_back, init_state


def render_password_protected():
    """
    Purpose: Inform the user the file is password protected and offer options.
    Per CLAUDE.md: never ask for the password. Offer guidance instead.
    """
    render_page_header()
    render_page_title("Password-protected file")
    st.divider()

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

    _render_go_back("upload")


def render_password_walkthrough():
    """
    Purpose: Guide the user through removing password protection.
    After following the steps, the user returns to upload a new file.
    """
    render_page_header()
    render_page_title("How to remove password protection")
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

    _render_go_back("password_protected")
