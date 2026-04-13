import logging
from django.views.generic import FormView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib.auth import login

logger = logging.getLogger('securite')

from .models import User, ProfilUtilisateur
from .forms import UtilisateurCreateForm, UtilisateurEditForm, PasswordChangeForm, MonProfilForm


class LoginView(FormView):
    """Vue de connexion"""
    template_name = 'accounts/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('dashboard:index')

    def get_form(self, form_class=None):
        """Passe le request au formulaire — requis par django-axes."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request, **self.get_form_kwargs())

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        logger.info(f"CONNEXION_OK user={user.email} ip={self.request.META.get('REMOTE_ADDR')}")
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(
            f"CONNEXION_ECHEC ip={self.request.META.get('REMOTE_ADDR')} "
            f"data={form.data.get('username', '')}"
        )
        return super().form_invalid(form)


# ── Mon profil (accessible à tous les utilisateurs connectés) ─────────────────

@login_required
def mon_profil(request):
    """Permet à n'importe quel utilisateur connecté de modifier son profil
    et de changer son mot de passe."""
    user = request.user
    pwd_form = PasswordChangeForm(user=user)
    profil_form = MonProfilForm(instance=user)

    if request.method == 'POST':
        if 'changer_password' in request.POST:
            pwd_form = PasswordChangeForm(user=user, data=request.POST)
            if pwd_form.is_valid():
                pwd_form.save()
                logger.info(
                    f"PASSWORD_CHANGE user={user.email} "
                    f"ip={request.META.get('REMOTE_ADDR')}"
                )
                messages.success(request, 'Mot de passe mis à jour avec succès.')
                return redirect('accounts:mon_profil')
        else:
            profil_form = MonProfilForm(request.POST, instance=user)
            if profil_form.is_valid():
                profil_form.save()
                messages.success(request, 'Profil mis à jour.')
                return redirect('accounts:mon_profil')

    return render(request, 'accounts/mon_profil.html', {
        'profil_form': profil_form,
        'pwd_form': pwd_form,
    })


# ── Helpers d'accès ───────────────────────────────────────────────────────────

def _peut_gerer_utilisateurs(request):
    """Retourne True si l'utilisateur connecté peut gérer des utilisateurs."""
    if request.user.is_superuser:
        return True
    if request.entreprise and hasattr(request.user, 'profil'):
        return request.user.profil.est_admin
    return False


# ── Gestion des utilisateurs ──────────────────────────────────────────────────

@login_required
def utilisateur_liste(request):
    entreprise = request.entreprise

    if not _peut_gerer_utilisateurs(request):
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard:index')

    if request.user.is_superuser:
        profils = ProfilUtilisateur.objects.all().select_related('utilisateur', 'entreprise')
    else:
        profils = ProfilUtilisateur.objects.filter(
            entreprise=entreprise
        ).select_related('utilisateur')

    return render(request, 'accounts/utilisateur_liste.html', {
        'profils': profils,
    })


@login_required
def utilisateur_creer(request):
    if not _peut_gerer_utilisateurs(request):
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:utilisateur_liste')

    if request.method == 'POST':
        form = UtilisateurCreateForm(
            request.POST,
            requesting_user=request.user,
            current_entreprise=request.entreprise,
        )
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Utilisateur « {user.nom_complet} » créé.')
            return redirect('accounts:utilisateur_liste')
    else:
        form = UtilisateurCreateForm(
            requesting_user=request.user,
            current_entreprise=request.entreprise,
        )

    return render(request, 'accounts/utilisateur_form.html', {
        'form': form,
        'titre': 'Nouvel utilisateur',
    })


@login_required
def utilisateur_modifier(request, pk):
    if not _peut_gerer_utilisateurs(request):
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:utilisateur_liste')

    profil = get_object_or_404(ProfilUtilisateur, pk=pk)

    # Un admin d'entreprise ne peut modifier que ses propres utilisateurs
    if not request.user.is_superuser and profil.entreprise != request.entreprise:
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:utilisateur_liste')

    user = profil.utilisateur

    # Formulaire mot de passe séparé
    pwd_form = PasswordChangeForm(user=user)
    form = UtilisateurEditForm(
        instance=user,
        requesting_user=request.user,
        profil=profil,
    )

    if request.method == 'POST':
        if 'changer_password' in request.POST:
            pwd_form = PasswordChangeForm(user=user, data=request.POST)
            if pwd_form.is_valid():
                pwd_form.save()
                messages.success(request, 'Mot de passe mis à jour.')
                return redirect('accounts:utilisateur_modifier', pk=pk)
        else:
            form = UtilisateurEditForm(
                request.POST,
                instance=user,
                requesting_user=request.user,
                profil=profil,
            )
            if form.is_valid():
                form.save()
                messages.success(request, f'Utilisateur « {user.nom_complet} » modifié.')
                return redirect('accounts:utilisateur_liste')

    return render(request, 'accounts/utilisateur_form.html', {
        'form': form,
        'pwd_form': pwd_form,
        'titre': f'Modifier — {user.nom_complet}',
        'profil': profil,
    })


@login_required
def utilisateur_toggle_actif(request, pk):
    entreprise = request.entreprise
    profil = get_object_or_404(ProfilUtilisateur, pk=pk)

    if not request.user.is_superuser:
        if profil.entreprise != entreprise:
            messages.error(request, 'Accès non autorisé.')
            return redirect('accounts:utilisateur_liste')
        if not request.user.profil.est_admin:
            messages.error(request, 'Accès réservé aux administrateurs.')
            return redirect('accounts:utilisateur_liste')

    if request.method == 'POST':
        profil.actif = not profil.actif
        profil.save(update_fields=['actif'])
        etat = 'activé' if profil.actif else 'désactivé'
        messages.success(request, f'Utilisateur {profil.utilisateur.nom_complet} {etat}.')

    return redirect('accounts:utilisateur_liste')


@login_required
def utilisateur_changer_role(request, pk):
    entreprise = request.entreprise
    profil = get_object_or_404(ProfilUtilisateur, pk=pk)

    if not request.user.is_superuser:
        if profil.entreprise != entreprise or not request.user.profil.est_admin:
            messages.error(request, 'Accès non autorisé.')
            return redirect('accounts:utilisateur_liste')

    if request.method == 'POST':
        nouveau_role = request.POST.get('role')
        if nouveau_role in dict(ProfilUtilisateur.Role.choices):
            profil.role = nouveau_role
            profil.save(update_fields=['role'])
            messages.success(request, f'Rôle mis à jour : {profil.get_role_display()}.')

    return redirect('accounts:utilisateur_liste')
