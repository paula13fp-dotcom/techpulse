"""Simple password gate for TechPulse.

Usage — call at the top of every page (after set_page_config):

    from techpulse.auth import require_login
    require_login()

The password is read from st.secrets["APP_PASSWORD"] (Streamlit Cloud)
or from the APP_PASSWORD env var (local dev).  If neither is set the
gate is disabled so local development is frictionless.
"""
from __future__ import annotations

import os
import streamlit as st


def _get_password() -> str | None:
    """Return the configured password, or None if auth is disabled."""
    try:
        pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        pw = ""
    return pw or os.getenv("APP_PASSWORD") or None


def require_login() -> None:
    """Show a login form and stop the page if the user is not authenticated."""
    password = _get_password()
    if not password:
        return  # Auth disabled — no password configured

    # Already logged in this session
    if st.session_state.get("authenticated"):
        return

    st.title("🔒 TechPulse — Acceso restringido")
    st.markdown("Introduce la contraseña para acceder al dashboard.")

    with st.form("login_form"):
        user_input = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")

    if submitted:
        if user_input == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")

    st.stop()  # Block the rest of the page until authenticated
