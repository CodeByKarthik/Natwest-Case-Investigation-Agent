from __future__ import annotations

import html

import streamlit as st
from natwest_frontend.auth.session import get_auth_url


def render_login() -> None:
    auth_url = html.escape(get_auth_url(), quote=True)

    st.html(
        f"""
        <style>
            /* Hide the existing Streamlit page title on the login screen */
            h1 {{
                display: none !important;
            }}

            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 34rem),
                    linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
            }}

            .block-container {{
                max-width: 960px;
                padding-top: 2rem;
                padding-bottom: 2rem;
            }}

            .login-shell {{
                min-height: 78vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .login-card {{
                width: 100%;
                max-width: 420px;
                padding: 2.5rem 2.25rem;
                border: 1px solid #e5e7eb;
                border-radius: 22px;
                background: rgba(255, 255, 255, 0.96);
                box-shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
                text-align: center;
            }}

            .login-icon {{
                margin: 0 auto 1.15rem;
                font-size: 5.5rem;
                line-height: 1;
                background: transparent;
                border: none;
                box-shadow: none;
            }}

            .app-title {{
                margin: 0 0 1.25rem;
                color: #0f172a;
                font-size: 2.25rem;
                font-weight: 800;
                line-height: 1.2;
                text-align: center;
            }}

            .login-title {{
                margin: 0 0 0.6rem;
                color: #111827;
                font-size: 1.55rem;
                font-weight: 800;
                line-height: 1.2;
            }}

            .login-copy {{
                margin: 0 auto 1.7rem;
                max-width: 320px;
                color: #64748b;
                font-size: 0.98rem;
                line-height: 1.55;
            }}

            .login-link {{
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                min-height: 48px;
                border-radius: 12px;
                background: #2563eb;
                color: #ffffff !important;
                text-decoration: none !important;
                font-size: 1rem;
                font-weight: 700;
                box-shadow: 0 10px 24px rgba(37, 99, 235, 0.24);
            }}

            .login-link:hover {{
                background: #1d4ed8;
                color: #ffffff !important;
                text-decoration: none !important;
            }}

            .login-note {{
                margin-top: 1.15rem;
                color: #94a3b8;
                font-size: 0.82rem;
            }}
        </style>

        <div class="login-shell">
            <div class="login-card">
                <div class="app-title">NatWest Investigation Agent</div>

                <div class="login-icon">🏦</div>

                <h2 class="login-title">Sign in required</h2>

                <p class="login-copy">
                    Use your NatWest account to continue.
                </p>

                <a href="{auth_url}" target="_self" class="login-link">
                    Login with Keycloak
                </a>

                <div class="login-note">
                    Secure authentication powered by Keycloak
                </div>
            </div>
        </div>
        """
    )