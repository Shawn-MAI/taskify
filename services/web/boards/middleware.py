"""Extra response headers for every page.

The Content-Security-Policy forbids inline scripts and styles, which backs up
Django's template auto-escaping against XSS (FR-011).
"""

from __future__ import annotations

CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"


class SecurityHeadersMiddleware:
    """Adds CSP and no-store caching headers to responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        if not request.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
