"""
apps/accounts/permissions.py
Décorateurs et mixins de contrôle d'accès par rôle
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


def role_requis(*roles):
    """
    Décorateur de vue : restreint l'accès aux rôles spécifiés.
    Usage : @role_requis('admin', 'gestionnaire')
    """
    def decorator(vue):
        @wraps(vue)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not hasattr(request.user, 'profil'):
                raise PermissionDenied
            if request.user.profil.role not in roles and not request.user.is_superuser:
                messages.error(request, 'Vous n\'avez pas les droits pour accéder à cette page.')
                return redirect('dashboard:index')
            return vue(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_requis(vue):
    """Raccourci : accès réservé aux administrateurs."""
    return role_requis('admin')(vue)


def gestionnaire_requis(vue):
    """Raccourci : accès réservé aux gestionnaires et admins."""
    return role_requis('admin', 'gestionnaire')(vue)


class TenantViewMixin:
    """
    Mixin pour les vues basées sur les classes.
    Filtre automatiquement les querysets par entreprise.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs.model, 'entreprise'):
            return qs.filter(entreprise=self.request.entreprise)
        return qs

    def form_valid(self, form):
        if hasattr(form.instance, 'entreprise_id') and not form.instance.entreprise_id:
            form.instance.entreprise = self.request.entreprise
        return super().form_valid(form)


class LoginTenantMixin(LoginRequiredMixin, TenantViewMixin):
    """Combinaison login requis + filtrage tenant."""
    pass


class AdminRequiredMixin(LoginTenantMixin):
    """Mixin : accès admin uniquement."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            if not hasattr(request.user, 'profil') or request.user.profil.role != 'admin':
                messages.error(request, 'Accès réservé aux administrateurs.')
                return redirect('dashboard:index')
        return super().dispatch(request, *args, **kwargs)


class GestionnaireRequiredMixin(LoginTenantMixin):
    """Mixin : accès gestionnaire ou admin."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            if not hasattr(request.user, 'profil') or \
               request.user.profil.role not in ('admin', 'gestionnaire'):
                messages.error(request, 'Vous n\'avez pas les droits nécessaires.')
                return redirect('dashboard:index')
        return super().dispatch(request, *args, **kwargs)
