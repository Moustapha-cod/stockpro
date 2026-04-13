"""
apps/common/middleware.py
Middlewares de sécurité personnalisés.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Ajoute les en-têtes de sécurité HTTP sur toutes les réponses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Anti-clickjacking (renforce X_FRAME_OPTIONS de Django)
        response['X-Frame-Options'] = 'DENY'

        # Empêche le MIME-sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Politique de référent
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Supprime la signature du serveur
        response['Server'] = 'StockPro'

        # Permissions navigateur (désactive fonctionnalités non utilisées)
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=()'
        )

        # Content Security Policy
        csp_parts = []
        csp_map = {
            'default-src': getattr(settings, 'CSP_DEFAULT_SRC', ("'self'",)),
            'script-src':  getattr(settings, 'CSP_SCRIPT_SRC',  ("'self'",)),
            'style-src':   getattr(settings, 'CSP_STYLE_SRC',   ("'self'", "'unsafe-inline'")),
            'font-src':    getattr(settings, 'CSP_FONT_SRC',    ("'self'",)),
            'img-src':     getattr(settings, 'CSP_IMG_SRC',     ("'self'", "data:")),
            'connect-src': getattr(settings, 'CSP_CONNECT_SRC', ("'self'",)),
            'frame-src':   getattr(settings, 'CSP_FRAME_SRC',   ("'none'",)),
        }
        for directive, sources in csp_map.items():
            csp_parts.append(f"{directive} {' '.join(sources)}")
        response['Content-Security-Policy'] = '; '.join(csp_parts)

        return response
