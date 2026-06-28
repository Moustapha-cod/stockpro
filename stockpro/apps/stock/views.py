"""apps/stock/views.py — CRUD Produits, Catégories, Fournisseurs, Mouvements"""

import csv
import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Produit, ProduitPhoto, Categorie, Fournisseur, MouvementStock, CompatibiliteVehicule
from .forms import ProduitForm, CategorieForm, FournisseurForm, MouvementStockForm, CompatibiliteFormSet
from apps.accounts.permissions import gestionnaire_requis
from apps.common.decorators import rate_limit


# ── Produits ──────────────────────────────────────────────────────────────────

@login_required
def produit_liste(request):
    entreprise = request.entreprise
    qs = Produit.objects.filter(entreprise=entreprise).select_related('categorie', 'fournisseur').prefetch_related('photos', 'compatibilites')

    q              = request.GET.get('q', '')
    categorie_id   = request.GET.get('categorie', '')
    statut         = request.GET.get('statut', '')
    type_vehicule  = request.GET.get('type_vehicule', '')
    marque         = request.GET.get('marque', '')
    compat_marque  = request.GET.get('compat_marque', '')
    compat_modele  = request.GET.get('compat_modele', '')
    compat_annee   = request.GET.get('compat_annee', '')

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(reference__icontains=q) |
            Q(code_barre__icontains=q) |
            Q(reference_oem__icontains=q) |
            Q(reference_equivalente__icontains=q) |
            Q(marque__icontains=q)
        )
    if categorie_id:
        qs = qs.filter(categorie_id=categorie_id)
    if type_vehicule:
        qs = qs.filter(type_vehicule=type_vehicule)
    if marque:
        qs = qs.filter(marque__icontains=marque)
    if statut == 'alerte':
        qs = qs.filter(quantite_stock__lte=F('seuil_alerte'), quantite_stock__gt=0)
    elif statut == 'rupture':
        qs = qs.filter(quantite_stock=0)
    elif statut == 'actif':
        qs = qs.filter(actif=True)

    # Filtres compatibilité véhicule (filtre sur les entrées CompatibiliteVehicule)
    if compat_marque or compat_modele or compat_annee:
        compat_qs = CompatibiliteVehicule.objects.filter(produit__entreprise=entreprise)
        if compat_marque:
            compat_qs = compat_qs.filter(marque__icontains=compat_marque)
        if compat_modele:
            compat_qs = compat_qs.filter(modele__icontains=compat_modele)
        if compat_annee:
            try:
                year = int(compat_annee)
                compat_qs = compat_qs.filter(
                    Q(annee_debut__isnull=True) | Q(annee_debut__lte=year),
                    Q(annee_fin__isnull=True) | Q(annee_fin__gte=year),
                )
            except ValueError:
                pass
        qs = qs.filter(pk__in=compat_qs.values_list('produit_id', flat=True))

    # Listes pour autocomplete
    marques_pieces = list(
        Produit.objects.filter(entreprise=entreprise, actif=True)
        .exclude(marque='').values_list('marque', flat=True).distinct().order_by('marque')
    )
    compat_marques = list(
        CompatibiliteVehicule.objects.filter(produit__entreprise=entreprise)
        .values_list('marque', flat=True).distinct().order_by('marque')
    )

    categories = Categorie.objects.filter(entreprise=entreprise, actif=True)
    panier = request.session.get('panier', [])

    total = qs.count()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'produits': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'categorie_id': categorie_id,
        'statut': statut,
        'type_vehicule': type_vehicule,
        'marque': marque,
        'compat_marque': compat_marque,
        'compat_modele': compat_modele,
        'compat_annee': compat_annee,
        'total': total,
        'type_vehicule_choices': Produit.TypeVehicule.choices,
        'marques_pieces_json': json.dumps(marques_pieces),
        'compat_marques_json': json.dumps(compat_marques),
        'panier_json': json.dumps(panier),
        'nb_panier': sum(item['quantite'] for item in panier),
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


def _compat_context(entreprise):
    """Données d'autocomplétion pour le formset de compatibilité."""
    marques = list(
        CompatibiliteVehicule.objects.filter(produit__entreprise=entreprise)
        .values_list('marque', flat=True).distinct().order_by('marque')
    )
    modeles = list(
        CompatibiliteVehicule.objects.filter(produit__entreprise=entreprise)
        .exclude(modele='').values('marque', 'modele').distinct().order_by('marque', 'modele')
    )
    return json.dumps(marques), json.dumps(modeles)


@login_required
@gestionnaire_requis
def produit_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, entreprise=entreprise)
        compat_fs = CompatibiliteFormSet(request.POST, prefix='compatibilites')
        if form.is_valid() and compat_fs.is_valid():
            produit = form.save(commit=False)
            produit.entreprise = entreprise
            produit.cree_par = request.user
            produit.save()
            compat_fs.instance = produit
            compat_fs.save()
            _sauvegarder_photos(request, produit)
            messages.success(request, f'Produit « {produit.nom} » créé avec succès.')
            return redirect('stock:produit_liste')
    else:
        form = ProduitForm(entreprise=entreprise)
        compat_fs = CompatibiliteFormSet(prefix='compatibilites')
    marques_json, modeles_json = _compat_context(entreprise)
    return render(request, 'stock/produit_form.html', {
        'form': form,
        'compat_formset': compat_fs,
        'titre': 'Nouveau produit',
        'marques_existantes': marques_json,
        'modeles_existants': modeles_json,
    })


@login_required
@gestionnaire_requis
def produit_modifier(request, pk):
    entreprise = request.entreprise
    produit = get_object_or_404(Produit, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        if 'photos_upload_only' in request.POST:
            _sauvegarder_photos(request, produit)
            nb = len(request.FILES.getlist('photos'))
            if nb:
                messages.success(request, f'{nb} photo(s) ajoutée(s).')
            return redirect('stock:produit_modifier', pk=pk)
        form = ProduitForm(request.POST, request.FILES, instance=produit, entreprise=entreprise)
        compat_fs = CompatibiliteFormSet(request.POST, instance=produit, prefix='compatibilites')
        if form.is_valid() and compat_fs.is_valid():
            form.save()
            compat_fs.save()
            messages.success(request, f'Produit « {produit.nom} » modifié.')
            return redirect('stock:produit_modifier', pk=pk)
    else:
        form = ProduitForm(instance=produit, entreprise=entreprise)
        compat_fs = CompatibiliteFormSet(instance=produit, prefix='compatibilites')
    marques_json, modeles_json = _compat_context(entreprise)
    return render(request, 'stock/produit_form.html', {
        'form': form,
        'compat_formset': compat_fs,
        'titre': 'Modifier le produit',
        'produit': produit,
        'photos': produit.photos.all(),
        'marques_existantes': marques_json,
        'modeles_existants': modeles_json,
    })


@login_required
def produit_photo_supprimer(request, pk):
    photo = get_object_or_404(ProduitPhoto, pk=pk, produit__entreprise=request.entreprise)
    produit = photo.produit
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
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    context = {
        'mouvements': page_obj,
        'page_obj': page_obj,
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
    return response


# ── API recherche produits (Tom Select) ───────────────────────────────────────

@login_required
@rate_limit(max_calls=60, period=60)
def api_produits_search(request):
    """Retourne une liste JSON de produits filtrés par nom, référence ou code-barres."""
    entreprise = request.entreprise
    q = request.GET.get('q', '').strip()

    qs = Produit.objects.filter(entreprise=entreprise, actif=True)
    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(reference__icontains=q) |
            Q(code_barre__icontains=q) |
            Q(reference_oem__icontains=q) |
            Q(reference_equivalente__icontains=q)
        )

    qs = qs.select_related('categorie').order_by('nom')[:30]

    results = []
    for p in qs:
        label = p.nom
        if p.reference:
            label += f' [{p.reference}]'
        if p.reference_oem:
            label += f' — OEM: {p.reference_oem}'
        results.append({
            'value': str(p.pk),
            'text': label,
            'stock': p.quantite_stock,
            'prix': str(p.prix_vente or 0),
            'statut': p.statut_stock,
        })

    return JsonResponse({'results': results})


# ── API suggestions compatibilité véhicule ────────────────────────────────────

@login_required
@rate_limit(max_calls=120, period=60)
def api_compat_suggestions(request):
    """Retourne les marques et modèles déjà enregistrés pour l'autocomplétion."""
    entreprise = request.entreprise
    marque_filtre = request.GET.get('marque', '').strip()

    qs = CompatibiliteVehicule.objects.filter(produit__entreprise=entreprise)

    if marque_filtre:
        modeles = list(
            qs.filter(marque__iexact=marque_filtre)
            .exclude(modele='')
            .values_list('modele', flat=True)
            .distinct().order_by('modele')
        )
        return JsonResponse({'modeles': modeles})

    marques = list(qs.values_list('marque', flat=True).distinct().order_by('marque'))
    return JsonResponse({'marques': marques})


# ── Panier (session) ──────────────────────────────────────────────────────────

def _panier_response(panier):
    total = sum(item['prix_vente'] * item['quantite'] for item in panier)
    nb = sum(item['quantite'] for item in panier)
    return JsonResponse({'panier': panier, 'total': total, 'nb': nb})


@login_required
def panier_ajouter(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    entreprise = request.entreprise
    produit = get_object_or_404(Produit, pk=pk, entreprise=entreprise)
    panier = request.session.get('panier', [])
    for item in panier:
        if item['pk'] == pk:
            item['quantite'] += 1
            break
    else:
        panier.append({
            'pk': pk,
            'nom': produit.nom,
            'reference': produit.reference or '',
            'prix_vente': int(produit.prix_vente or 0),
            'quantite': 1,
        })
    request.session['panier'] = panier
    request.session.modified = True
    return _panier_response(panier)


@login_required
def panier_retirer(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    panier = [item for item in request.session.get('panier', []) if item['pk'] != pk]
    request.session['panier'] = panier
    request.session.modified = True
    return _panier_response(panier)


@login_required
def panier_maj_quantite(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        quantite = max(1, int(data.get('quantite', 1)))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    panier = request.session.get('panier', [])
    for item in panier:
        if item['pk'] == pk:
            item['quantite'] = quantite
            break
    request.session['panier'] = panier
    request.session.modified = True
    return _panier_response(panier)


@login_required
def panier_vider(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    request.session['panier'] = []
    request.session.modified = True
    return _panier_response([])


@login_required
def panier_info(request):
    panier = request.session.get('panier', [])
    return _panier_response(panier)
