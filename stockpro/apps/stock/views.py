"""apps/stock/views.py — CRUD Produits, Catégories, Fournisseurs, Mouvements"""

import csv
import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Produit, ProduitPhoto, Categorie, Fournisseur, MouvementStock
from .forms import ProduitForm, CategorieForm, FournisseurForm, MouvementStockForm
from apps.accounts.permissions import gestionnaire_requis


# ── Produits ──────────────────────────────────────────────────────────────────

@login_required
def produit_liste(request):
    entreprise = request.entreprise
    qs = Produit.objects.filter(entreprise=entreprise).select_related('categorie', 'fournisseur').prefetch_related('photos')

    q = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')
    statut = request.GET.get('statut', '')

    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(reference__icontains=q) | Q(code_barre__icontains=q))
    if categorie_id:
        qs = qs.filter(categorie_id=categorie_id)
    if statut == 'alerte':
        from django.db.models import F
        qs = qs.filter(quantite_stock__lte=F('seuil_alerte'), quantite_stock__gt=0)
    elif statut == 'rupture':
        qs = qs.filter(quantite_stock=0)
    elif statut == 'actif':
        qs = qs.filter(actif=True)

    categories = Categorie.objects.filter(entreprise=entreprise, actif=True)
    context = {
        'produits': qs,
        'categories': categories,
        'q': q,
        'categorie_id': categorie_id,
        'statut': statut,
        'total': qs.count(),
    }
    return render(request, 'stock/produit_liste.html', context)


MAX_PHOTOS_PAR_PRODUIT = 10  # Limite anti-DoS


def _sauvegarder_photos(request, produit):
    """Enregistre les fichiers du champ multi-upload 'photos' après validation."""
    from apps.common.validators import valider_image
    from django.core.exceptions import ValidationError
    from django.contrib import messages as msg

    fichiers = request.FILES.getlist('photos')

    # Vérifier la limite totale (existantes + nouvelles)
    nb_existantes = produit.photos.count()
    places_restantes = MAX_PHOTOS_PAR_PRODUIT - nb_existantes
    if len(fichiers) > places_restantes:
        msg.warning(request,
            f"Limite de {MAX_PHOTOS_PAR_PRODUIT} photos atteinte. "
            f"Seulement {max(places_restantes, 0)} photo(s) acceptée(s).")
        fichiers = fichiers[:max(places_restantes, 0)]

    for f in fichiers:
        try:
            valider_image(f)
            ProduitPhoto.objects.create(produit=produit, image=f)
        except ValidationError as e:
            msg.error(request, f"Photo « {f.name} » rejetée : {e.message}")


@login_required
@gestionnaire_requis
def produit_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, entreprise=entreprise)
        if form.is_valid():
            produit = form.save(commit=False)
            produit.entreprise = entreprise
            produit.cree_par = request.user
            produit.save()
            _sauvegarder_photos(request, produit)
            messages.success(request, f'Produit « {produit.nom} » créé avec succès.')
            return redirect('stock:produit_liste')
    else:
        form = ProduitForm(entreprise=entreprise)
    return render(request, 'stock/produit_form.html', {'form': form, 'titre': 'Nouveau produit'})


@login_required
@gestionnaire_requis
def produit_modifier(request, pk):
    entreprise = request.entreprise
    produit = get_object_or_404(Produit, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        if 'photos_upload_only' in request.POST:
            # Upload de photos supplémentaires uniquement
            _sauvegarder_photos(request, produit)
            nb = len(request.FILES.getlist('photos'))
            if nb:
                messages.success(request, f'{nb} photo(s) ajoutée(s).')
            return redirect('stock:produit_modifier', pk=pk)
        form = ProduitForm(request.POST, request.FILES, instance=produit, entreprise=entreprise)
        if form.is_valid():
            form.save()
            messages.success(request, f'Produit « {produit.nom} » modifié.')
            return redirect('stock:produit_modifier', pk=pk)
    else:
        form = ProduitForm(instance=produit, entreprise=entreprise)
    return render(request, 'stock/produit_form.html', {
        'form': form,
        'titre': 'Modifier le produit',
        'produit': produit,
        'photos': produit.photos.all(),
    })


@login_required
def produit_photo_supprimer(request, pk):
    photo = get_object_or_404(ProduitPhoto, pk=pk)
    produit = photo.produit
    if produit.entreprise != request.entreprise:
        messages.error(request, 'Accès non autorisé.')
        return redirect('stock:produit_liste')
    if request.method == 'POST':
        photo.image.delete(save=False)
        photo.delete()
    return redirect('stock:produit_modifier', pk=produit.pk)


@login_required
@gestionnaire_requis
def produit_supprimer(request, pk):
    entreprise = request.entreprise
    produit = get_object_or_404(Produit, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        nom = produit.nom
        produit.actif = False
        produit.save(update_fields=['actif'])
        messages.success(request, f'Produit « {nom} » désactivé.')
        return redirect('stock:produit_liste')
    return render(request, 'stock/confirmer_suppression.html', {'objet': produit, 'type': 'produit'})


# ── Catégories ────────────────────────────────────────────────────────────────

@login_required
def categorie_liste(request):
    entreprise = request.entreprise
    categories = Categorie.objects.filter(entreprise=entreprise)
    return render(request, 'stock/categorie_liste.html', {'categories': categories})


@login_required
def categorie_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.entreprise = entreprise
            cat.save()
            messages.success(request, f'Catégorie « {cat.nom} » créée.')
            return redirect('stock:categorie_liste')
    else:
        form = CategorieForm()
    return render(request, 'stock/categorie_form.html', {'form': form, 'titre': 'Nouvelle catégorie'})


@login_required
def categorie_modifier(request, pk):
    entreprise = request.entreprise
    cat = get_object_or_404(Categorie, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Catégorie « {cat.nom} » modifiée.')
            return redirect('stock:categorie_liste')
    else:
        form = CategorieForm(instance=cat)
    return render(request, 'stock/categorie_form.html', {'form': form, 'titre': 'Modifier la catégorie', 'objet': cat})


# ── Fournisseurs ──────────────────────────────────────────────────────────────

@login_required
def fournisseur_liste(request):
    entreprise = request.entreprise
    q = request.GET.get('q', '')
    qs = Fournisseur.objects.filter(entreprise=entreprise)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(telephone__icontains=q) | Q(email__icontains=q))
    return render(request, 'stock/fournisseur_liste.html', {'fournisseurs': qs, 'q': q})


@login_required
def fournisseur_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.entreprise = entreprise
            f.save()
            messages.success(request, f'Fournisseur « {f.nom} » créé.')
            return redirect('stock:fournisseur_liste')
    else:
        form = FournisseurForm()
    return render(request, 'stock/fournisseur_form.html', {'form': form, 'titre': 'Nouveau fournisseur'})


@login_required
def fournisseur_modifier(request, pk):
    entreprise = request.entreprise
    fournisseur = get_object_or_404(Fournisseur, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, f'Fournisseur « {fournisseur.nom} » modifié.')
            return redirect('stock:fournisseur_liste')
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, 'stock/fournisseur_form.html', {'form': form, 'titre': 'Modifier le fournisseur', 'objet': fournisseur})


# ── Mouvements de stock ───────────────────────────────────────────────────────

@login_required
def mouvement_liste(request):
    entreprise = request.entreprise
    qs = MouvementStock.objects.filter(entreprise=entreprise).select_related('produit', 'cree_par')
    type_filtre = request.GET.get('type', '')
    if type_filtre and type_filtre in dict(MouvementStock.TypeMouvement.choices):
        qs = qs.filter(type_mouvement=type_filtre)
    context = {
        'mouvements': qs[:100],
        'type_filtre': type_filtre,
        'types': MouvementStock.TypeMouvement.choices,
    }
    return render(request, 'stock/mouvement_liste.html', context)


@login_required
@gestionnaire_requis
def mouvement_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = MouvementStockForm(request.POST, entreprise=entreprise)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.entreprise = entreprise
            mouvement.cree_par = request.user
            mouvement.save()
            messages.success(request, 'Mouvement de stock enregistré.')
            return redirect('stock:mouvement_liste')
    else:
        form = MouvementStockForm(entreprise=entreprise)
    return render(request, 'stock/mouvement_form.html', {'form': form})


# ── Inventaire ────────────────────────────────────────────────────────────────

@login_required
def inventaire(request):
    entreprise = request.entreprise

    qs = Produit.objects.filter(
        entreprise=entreprise, actif=True
    ).select_related('categorie', 'fournisseur').order_by('categorie__nom', 'nom')

    # Filtres
    q           = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')
    statut      = request.GET.get('statut', '')
    fournisseur_id = request.GET.get('fournisseur', '')

    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(reference__icontains=q) | Q(code_barre__icontains=q) | Q(marque__icontains=q))
    if categorie_id:
        qs = qs.filter(categorie_id=categorie_id)
    if fournisseur_id:
        qs = qs.filter(fournisseur_id=fournisseur_id)
    if statut == 'rupture':
        qs = qs.filter(quantite_stock=0)
    elif statut == 'alerte':
        qs = qs.filter(quantite_stock__gt=0, quantite_stock__lte=F('seuil_alerte'))
    elif statut == 'normal':
        qs = qs.filter(quantite_stock__gt=F('seuil_alerte'))

    # Totaux
    totaux = qs.aggregate(
        total_articles=Sum('quantite_stock'),
        valeur_achat=Sum(F('quantite_stock') * F('prix_achat')),
        valeur_vente=Sum(F('quantite_stock') * F('prix_vente')),
    )

    nb_rupture = qs.filter(quantite_stock=0).count()
    nb_alerte  = qs.filter(quantite_stock__gt=0, quantite_stock__lte=F('seuil_alerte')).count()

    categories  = Categorie.objects.filter(entreprise=entreprise, actif=True).order_by('nom')
    fournisseurs = Fournisseur.objects.filter(entreprise=entreprise, actif=True).order_by('nom')

    context = {
        'produits': qs,
        'categories': categories,
        'fournisseurs': fournisseurs,
        'totaux': totaux,
        'nb_rupture': nb_rupture,
        'nb_alerte': nb_alerte,
        'nb_total': qs.count(),
        # Filtres actifs
        'q': q,
        'categorie_id': categorie_id,
        'fournisseur_id': fournisseur_id,
        'statut': statut,
    }
    return render(request, 'stock/inventaire.html', context)


@login_required
def inventaire_export(request):
    import logging
    logger = logging.getLogger('securite')
    entreprise = request.entreprise
    logger.info(
        f"EXPORT_CSV_INVENTAIRE user={request.user.email} "
        f"entreprise={entreprise} ip={request.META.get('REMOTE_ADDR')}"
    )

    qs = Produit.objects.filter(
        entreprise=entreprise, actif=True
    ).select_related('categorie', 'fournisseur').order_by('categorie__nom', 'nom')

    # Appliquer les mêmes filtres que la vue
    q            = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')
    statut       = request.GET.get('statut', '')
    fournisseur_id = request.GET.get('fournisseur', '')

    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(reference__icontains=q) | Q(code_barre__icontains=q))
    if categorie_id:
        qs = qs.filter(categorie_id=categorie_id)
    if fournisseur_id:
        qs = qs.filter(fournisseur_id=fournisseur_id)
    if statut == 'rupture':
        qs = qs.filter(quantite_stock=0)
    elif statut == 'alerte':
        qs = qs.filter(quantite_stock__gt=0, quantite_stock__lte=F('seuil_alerte'))
    elif statut == 'normal':
        qs = qs.filter(quantite_stock__gt=F('seuil_alerte'))

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="inventaire_{date.today()}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Référence', 'Code barre', 'Produit', 'Marque', 'Modèles compatibles',
        'Catégorie', 'Fournisseur', 'Emplacement', 'Unité',
        'Stock actuel', 'Seuil alerte', 'Statut',
        'Prix achat (FCFA)', 'Prix vente (FCFA)', 'Marge (FCFA)', 'Taux marge (%)',
        'Valeur stock achat (FCFA)', 'Valeur stock vente (FCFA)',
    ])

    for p in qs:
        if p.quantite_stock == 0:
            statut_label = 'Rupture'
        elif p.seuil_alerte and p.quantite_stock <= p.seuil_alerte:
            statut_label = 'Alerte'
        else:
            statut_label = 'Normal'

        writer.writerow([
            p.reference or '',
            p.code_barre or '',
            p.nom,
            p.marque or '',
            p.modele_compatible or '',
            p.categorie.nom if p.categorie else '',
            p.fournisseur.nom if p.fournisseur else '',
            p.emplacement or '',
            p.unite or 'Pièce',
            p.quantite_stock or 0,
            p.seuil_alerte or 0,
            statut_label,
            p.prix_achat or 0,
            p.prix_vente or 0,
            round(p.marge, 0),
            round(p.taux_marge, 1),
            round((p.quantite_stock or 0) * (p.prix_achat or 0), 0),
            round((p.quantite_stock or 0) * (p.prix_vente or 0), 0),
        ])

    # Ligne totaux
    totaux = qs.aggregate(
        total_articles=Sum('quantite_stock'),
        valeur_achat=Sum(F('quantite_stock') * F('prix_achat')),
        valeur_vente=Sum(F('quantite_stock') * F('prix_vente')),
    )
    writer.writerow([])
    writer.writerow([
        'TOTAL', '', '', '', '', '', '', '', '',
        totaux['total_articles'] or 0, '', '', '', '', '', '',
        round(totaux['valeur_achat'] or 0, 0),
        round(totaux['valeur_vente'] or 0, 0),
    ])


# ── API recherche produits (Tom Select) ───────────────────────────────────────

@login_required
def api_produits_search(request):
    """Retourne une liste JSON de produits filtrés par nom, référence ou code-barres."""
    entreprise = request.entreprise
    q = request.GET.get('q', '').strip()

    qs = Produit.objects.filter(entreprise=entreprise, actif=True)
    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(reference__icontains=q) |
            Q(code_barre__icontains=q)
        )

    qs = qs.select_related('categorie').order_by('nom')[:30]

    results = []
    for p in qs:
        label = p.nom
        if p.reference:
            label += f' [{p.reference}]'
        results.append({
            'value': str(p.pk),
            'text': label,
            'stock': p.quantite_stock,
            'prix': str(p.prix_vente or 0),
            'statut': p.statut_stock,
        })

    return JsonResponse({'results': results})

    return response
