"""Middleware for Neo Bloggy application."""

import time

from flask import session

from neo_bloggy.auth import get_csp_nonce, get_current_user
from neo_bloggy.caching import clear_expired_cache
from neo_bloggy.config import CACHE_ENABLED

# Security header values
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Cross-Origin-Opener-Policy": "same-origin",
}

# CSP policy components (nonce injected at runtime)
CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": (
        "'self' 'nonce-{nonce}' https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com https://platform.twitter.com "
        "https://syndication.twitter.com https://www.googletagmanager.com "
        "https://use.fontawesome.com https://maxcdn.bootstrapcdn.com "
        "https://static.cloudflareinsights.com"
    ),
    "style-src": (
        "'self' 'unsafe-inline' 'unsafe-hashes' https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com https://fonts.googleapis.com "
        "https://use.fontawesome.com https://maxcdn.bootstrapcdn.com"
    ),
    "img-src": "'self' data: blob: https:",
    "font-src": (
        "'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com "
        "https://use.fontawesome.com https://maxcdn.bootstrapcdn.com"
    ),
    "connect-src": (
        "'self' https://www.google-analytics.com https://cdn.jsdelivr.net "
        "https://static.cloudflareinsights.com"
    ),
    "frame-ancestors": "'none'",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}


def _build_csp_policy(nonce: str) -> str:
    """Build Content Security Policy string with the given nonce."""
    parts = []
    for directive, value in CSP_DIRECTIVES.items():
        # Inject nonce into directives that support it
        if "{nonce}" in value:
            value = value.format(nonce=nonce)
        parts.append(f"{directive} {value}")
    return "; ".join(parts) + ";"


class Middleware:
    """Middleware class for common request/response processing."""

    @staticmethod
    def after_request(response):
        """Process HTML responses for minification and clean up expired cache."""
        # Clean up expired cache entries periodically (roughly every minute)
        if CACHE_ENABLED and int(time.time()) % 60 == 0:
            clear_expired_cache()

        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # Remove any previously set CSP headers to avoid conflicts
        response.headers.pop("Content-Security-Policy", None)
        response.headers.pop("Content-Security-Policy-Report-Only", None)

        # Add Content Security Policy with nonce-based protection
        csp_nonce = get_csp_nonce()
        response.headers["Content-Security-Policy"] = _build_csp_policy(
            csp_nonce
        )

        # Update session with current user info
        user = get_current_user()
        if user:
            session["user"] = user["name"]

        return response
