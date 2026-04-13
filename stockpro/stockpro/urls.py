"""StockPro SN — Configuration des URLs"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from decouple import config


class StockProAdminSite(AdminSite):
    """Admin site avec tableau de bord personnalisé."""

    def index(self, request, extra_context=None):
        from apps.tenants.models import Entreprise
        from apps.accounts.models import User, ProfilUtilisateur

        entreprises = Entreprise.objects.order_by('-actif', 'nom')
        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_entreprises': entreprises.count(),
            'actives':           entreprises.filter(actif=True).count(),
            'inactives':         entreprises.filter(actif=False).count(),
            'total_users':       User.objects.count(),
            'users_actifs':      ProfilUtilisateur.objects.filter(actif=True).count(),
        }
        extra_context['entreprises'] = [
            {'entreprise': e,
             'nb_users': ProfilUtilisateur.objects.filter(entreprise=e, actif=True).count()}
            for e in entreprises
        ]
        extra_context['derniers_users'] = ProfilUtilisateur.objects.select_related(
            'utilisateur', 'entreprise'
        ).order_by('-date_creation')[:8]
        return super().index(request, extra_context)


# Remplacer la classe du site admin par défaut (conserve tous les modèles enregistrés)
admin.site.__class__ = StockProAdminSite

ADMIN_URL = config('ADMIN_URL', default='gestion-plateforme/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),

    # Redirection de la racine vers le dashboard
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),

    # Authentification
    path('', include('apps.accounts.urls', namespace='accounts')),

    # Tableau de bord
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),

    # Gestion de stock
    path('stock/', include('apps.stock.urls', namespace='stock')),

    # Facturation & paiements
    path('facturation/', include('apps.facturation.urls', namespace='facturation')),

    # Paramètres entreprise
    path('entreprise/', include('apps.tenants.urls', namespace='tenants')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personnalisation de l'interface admin
admin.site.site_header = 'StockPro SN — Administration'
admin.site.site_title = 'StockPro SN'
admin.site.index_title = 'Panneau d\'administration'
