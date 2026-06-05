"""apps/common/context_processors.py — Processeurs de contexte globaux"""


def csp_nonce(request):
    """Expose le nonce CSP généré par SecurityHeadersMiddleware aux templates."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
