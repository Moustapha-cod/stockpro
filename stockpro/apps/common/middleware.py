"""
apps/common/middleware.py
Middlewares de sécurité personnalisés.
"""

import secrets
import base64
from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Ajoute les en-têtes de sécurité HTTP sur toutes les réponses.
    Génère un nonce CSP par requête pour supprimer 'unsafe-inline' côté scripts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Nonce CSP unique par requête — partagé avec les templates via request.csp_nonce
        nonce = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
        request.csp_nonce = nonce

        response = self.get_response(request)

        # Anti-clickjacking
        response['X-Frame-Options'] = 'DENY'
        # Empêche le MIME-sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        # Politique de référent
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Supprime la signature du serveur
        response['Server'] = 'StockPro'
        # Permissions navigateur
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=()'
        )

        # script-src : injecte le nonce dynamiquement.
        # Les navigateurs supportant les nonces ignorent automatiquement 'unsafe-inline'.
        # 'unsafe-inline' reste en fallback pour les très vieux navigateurs.
        base_script_src = list(getattr(settings, 'CSP_SCRIPT_SRC', ("'self'",)))
        script_src_with_nonce = base_script_src + [f"'nonce-{nonce}'"]

        csp_map = {
            'default-src': getattr(settings, 'CSP_DEFAULT_SRC', ("'self'",)),
            'script-src':  tuple(script_src_with_nonce),
            'style-src':   getattr(settings, 'CSP_STYLE_SRC',   ("'self'", "'unsafe-inline'")),
            'font-src':    getattr(settings, 'CSP_FONT_SRC',    ("'self'",)),
            'img-src':     getattr(settings, 'CSP_IMG_SRC',     ("'self'", "data:")),
            'connect-src': getattr(settings, 'CSP_CONNECT_SRC', ("'self'",)),
            'frame-src':   getattr(settings, 'CSP_FRAME_SRC',   ("'none'",)),
        }
        csp_parts = [f"{d} {' '.join(s)}" for d, s in csp_map.items()]
        response['Content-Security-Policy'] = '; '.join(csp_parts)

        return response
