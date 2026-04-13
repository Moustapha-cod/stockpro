"""apps/tenants/views.py"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, F, Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Entreprise
from .forms import EntrepriseForm


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)


# ── Paramètres de l'entreprise courante (utilisateurs métier) ─────────────────

@login_required
def parametres(request):
    entreprise = request.entreprise

    if entreprise is None:
        messages.error(request, 'Aucune entreprise associée à votre compte.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = EntrepriseForm(request.POST, request.FILES, instance=entreprise)
        if form.is_valid():
            form.save()
            messages.success(request, 'Paramètres enregistrés avec succès.')
            return redirect('tenants:parametres')
    else:
        form = EntrepriseForm(instance=entreprise)

    return render(request, 'tenants/parametres.html', {
        'form': form,
        'entreprise': entreprise,
    })


# ── Panneau de gestion de la plateforme (superuser uniquement) ────────────────

@login_required
@superuser_required
def platform(request):
    """Tableau de bord du superuser — liste des entreprises actives."""
    from apps.accounts.models import ProfilUtilisateur
    from apps.stock.models import Produit
    from apps.facturation.models import Facture

    entreprises = Entreprise.objects.order_by('-actif', 'nom')

    # Ajouter des stats par entreprise
    stats = []
    for e in entreprises:
        nb_users    = ProfilUtilisateur.objects.filter(entreprise=e, actif=True).count()
        nb_produits = Produit.objects.filter(entreprise=e, actif=True).count()
        nb_factures = Facture.objects.filter(entreprise=e).count()
        stats.append({
            'entreprise': e,
            'nb_users': nb_users,
            'nb_produits': nb_produits,
            'nb_factures': nb_factures,
        })

    context = {
        'stats': stats,
        'nb_total': entreprises.count(),
        'nb_actives': entreprises.filter(actif=True).count(),
        'nb_inactives': entreprises.filter(actif=False).count(),
    }
    return render(request, 'tenants/platform.html', context)


@login_required
@superuser_required
def platform_creer(request):
    """Créer une nouvelle entreprise."""
    if request.method == 'POST':
        form = EntrepriseForm(request.POST, request.FILES)
        if form.is_valid():
            entreprise = form.save(commit=False)
            # Générer un slug unique à partir du nom
            from django.utils.text import slugify
            base_slug = slugify(entreprise.nom) or 'entreprise'
            slug = base_slug
            n = 1
            while Entreprise.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            entreprise.slug = slug
            entreprise.save()
            messages.success(request, f'Entreprise « {entreprise.nom} » créée.')
            return redirect('tenants:platform')
    else:
        form = EntrepriseForm()

    return render(request, 'tenants/entreprise_form.html', {
        'form': form,
        'titre': 'Nouvelle entreprise',
    })


@login_required
@superuser_required
def platform_modifier(request, pk):
    """Modifier une entreprise existante."""
    entreprise = get_object_or_404(Entreprise, pk=pk)

    if request.method == 'POST':
        form = EntrepriseForm(request.POST, request.FILES, instance=entreprise)
        if form.is_valid():
            form.save()
            messages.success(request, f'Entreprise « {entreprise.nom} » modifiée.')
            return redirect('tenants:platform')
    else:
        form = EntrepriseForm(instance=entreprise)

    return render(request, 'tenants/entreprise_form.html', {
        'form': form,
        'titre': f'Modifier — {entreprise.nom}',
        'entreprise': entreprise,
    })


@login_required
@superuser_required
def platform_toggle(request, pk):
    """Activer / désactiver une entreprise."""
    entreprise = get_object_or_404(Entreprise, pk=pk)
    if request.method == 'POST':
        entreprise.actif = not entreprise.actif
        entreprise.save(update_fields=['actif'])
        etat = 'activée' if entreprise.actif else 'désactivée'
        messages.success(request, f'Entreprise « {entreprise.nom} » {etat}.')
    return redirect('tenants:platform')


@login_required
@superuser_required
def platform_supprimer(request, pk):
    """Supprimer une entreprise et toutes ses données."""
    entreprise = get_object_or_404(Entreprise, pk=pk)
    if request.method == 'POST':
        nom = entreprise.nom
        entreprise.delete()
        messages.success(request, f'Entreprise « {nom} » supprimée définitivement.')
        return redirect('tenants:platform')

    return render(request, 'tenants/entreprise_confirmer_suppression.html', {
        'entreprise': entreprise,
    })
