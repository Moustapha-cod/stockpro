"""
apps/tenants/middleware.py
Middleware d'isolation — injecte l'entreprise courante dans chaque requête
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


class TenantMiddleware:
    """
    Injecte request.entreprise sur chaque requête authentifiée.
    Si l'utilisateur n'a pas d'entreprise associée → redirection.
    """

    URLS_EXEMPTEES = [
        '/static/',
        '/media/',
    ]

    def _urls_exemptees_dynamiques(self):
        return [
            reverse('accounts:login'),
            reverse('accounts:logout'),
            reverse('tenants:platform'),
            reverse('admin:index'),
        ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.entreprise = None

        if request.user.is_authenticated:
            if request.user.is_superuser:
                # Le superuser gère la plateforme uniquement
                request.entreprise = None
                # Bloquer l'accès aux pages métier
                url_courante = request.path
                pages_metier = ['/stock/', '/facturation/', '/dashboard/']
                if any(url_courante.startswith(p) for p in pages_metier):
                    messages.warning(request, 'Accès réservé aux utilisateurs d\'une entreprise.')
                    return redirect('tenants:platform')
            elif hasattr(request.user, 'profil') and request.user.profil.entreprise:
                request.entreprise = request.user.profil.entreprise
            else:
                # Utilisateur sans entreprise → redirection
                url_courante = request.path
                prefixes_exemptes = self.URLS_EXEMPTEES + self._urls_exemptees_dynamiques()
                est_exemptee = any(url_courante.startswith(u) for u in prefixes_exemptes)
                if not est_exemptee:
                    messages.warning(
                        request,
                        'Votre compte n\'est rattaché à aucune entreprise. '
                        'Contactez votre administrateur.'
                    )
                    return redirect(reverse('accounts:login'))

        response = self.get_response(request)
        return response
