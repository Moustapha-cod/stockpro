"""
apps/dashboard/views.py
Tableau de bord — KPIs, graphiques, alertes
"""

import csv
import json
from decimal import Decimal
from datetime import timedelta, date


def json_safe(data):
    """JSON safe pour intégration dans balises <script> HTML (échappe <, >, &)."""
    return json.dumps(data, ensure_ascii=False) \
               .replace('<', r'\u003c') \
               .replace('>', r'\u003e') \
               .replace('&', r'\u0026')

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.stock.models import Produit, MouvementStock, Categorie
from apps.facturation.models import Facture, LigneFacture, Paiement


@login_required
def index(request):
    """Vue principale du tableau de bord."""
    # Le superuser est redirigé vers son panneau de gestion de la plateforme
    if request.user.is_superuser:
        from django.shortcuts import redirect
        return redirect('tenants:platform')

    entreprise = request.entreprise
    aujourd_hui = date.today()

    # ── Période sélectionnée ──────────────────────────────────────────────────
    periode    = request.GET.get('periode', '30')
    date_debut = request.GET.get('date_debut', '')
    date_fin   = request.GET.get('date_fin', '')

    if periode == 'today':
        debut_periode = aujourd_hui
        fin_periode   = aujourd_hui
        jours = 1
    elif date_debut:
        from datetime import datetime as dt
        try:
            debut_periode = dt.strptime(date_debut, '%Y-%m-%d').date()
        except ValueError:
            debut_periode = aujourd_hui - timedelta(days=30)
        try:
            fin_periode = dt.strptime(date_fin, '%Y-%m-%d').date() if date_fin else aujourd_hui
        except ValueError:
            fin_periode = aujourd_hui
        jours = (fin_periode - debut_periode).days + 1
        periode = 'custom'
    else:
        jours = int(periode) if periode in ('7', '30', '90', '365') else 30
        debut_periode = aujourd_hui - timedelta(days=jours)
        fin_periode   = aujourd_hui

    # Filtre de date selon le mode
    if periode in ('today', 'custom'):
        filtre_date = {'date_emission__gte': debut_periode, 'date_emission__lte': fin_periode}
    else:
        filtre_date = {'date_emission__gte': debut_periode}

    # ── KPIs ──────────────────────────────────────────────────────────────────
    # Chiffre d'affaires de la période
    ca_periode = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
        **filtre_date
    ).aggregate(total=Sum('montant_ttc'))['total'] or Decimal('0')

    # Comparaison avec la période précédente (pas applicable en mode custom/today)
    evolution_ca = 0
    if periode not in ('today', 'custom'):
        debut_precedent = debut_periode - timedelta(days=jours)
        ca_precedent = Facture.objects.filter(
            entreprise=entreprise,
            statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
            date_emission__range=[debut_precedent, debut_periode]
        ).aggregate(total=Sum('montant_ttc'))['total'] or Decimal('0')
        if ca_precedent > 0:
            evolution_ca = round(((ca_periode - ca_precedent) / ca_precedent) * 100, 1)

    # Nombre de ventes (factures émises)
    nb_ventes = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
        **filtre_date
    ).count()

    # Valeur totale du stock
    valeur_stock = Produit.objects.filter(
        entreprise=entreprise,
        actif=True
    ).aggregate(
        total=Sum(F('quantite_stock') * F('prix_achat'))
    )['total'] or Decimal('0')

    nb_articles = Produit.objects.filter(entreprise=entreprise, actif=True).aggregate(
        total=Sum('quantite_stock')
    )['total'] or 0

    # Créances impayées
    creances = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE]
    ).aggregate(
        total=Sum(F('montant_ttc') - F('montant_paye'))
    )['total'] or Decimal('0')

    nb_factures_impayees = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE]
    ).count()

    # ── Graphique ventes journalières ─────────────────────────────────────────
    ventes_par_jour = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
        **filtre_date
    ).annotate(
        jour=TruncDay('date_emission')
    ).values('jour').annotate(
        total=Sum('montant_ttc'),
        count=Count('id')
    ).order_by('jour')

    labels_ventes = []
    data_ventes = []
    for v in ventes_par_jour:
        labels_ventes.append(v['jour'].strftime('%d/%m'))
        data_ventes.append(int(v['total']))

    # ── Alertes stock faible ──────────────────────────────────────────────────
    produits_alerte = Produit.objects.filter(
        entreprise=entreprise,
        actif=True,
        quantite_stock__lte=F('seuil_alerte')
    ).order_by('quantite_stock')[:10]

    # ── Dernières factures ────────────────────────────────────────────────────
    dernieres_factures = Facture.objects.filter(
        entreprise=entreprise
    ).select_related('client').order_by('-date_emission')[:8]

    # ── Top produits vendus ───────────────────────────────────────────────────
    top_produits = LigneFacture.objects.filter(
        facture__entreprise=entreprise,
        facture__statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
        **{'facture__' + k: v for k, v in filtre_date.items()}
    ).values(
        'produit__nom', 'produit__reference'
    ).annotate(
        total_vendu=Sum('quantite'),
        ca=Sum(F('quantite') * F('prix_unitaire_ht'))
    ).order_by('-total_vendu')[:5]

    # ── Répartition par catégorie ─────────────────────────────────────────────
    repartition_categories = LigneFacture.objects.filter(
        facture__entreprise=entreprise,
        produit__categorie__isnull=False,
        **{'facture__' + k: v for k, v in filtre_date.items()}
    ).values(
        'produit__categorie__nom', 'produit__categorie__couleur'
    ).annotate(
        total=Sum(F('quantite') * F('prix_unitaire_ht'))
    ).order_by('-total')[:6]

    labels_cat = [r['produit__categorie__nom'] for r in repartition_categories]
    data_cat = [int(r['total']) for r in repartition_categories]

    context = {
        'periode': periode,
        'jours': jours,
        'date_debut': date_debut,
        'date_fin': date_fin,
        # KPIs
        'ca_periode': ca_periode,
        'evolution_ca': evolution_ca,
        'nb_ventes': nb_ventes,
        'valeur_stock': valeur_stock,
        'nb_articles': nb_articles,
        'creances': creances,
        'nb_factures_impayees': nb_factures_impayees,
        # Graphiques
        'labels_ventes': json_safe(labels_ventes),
        'data_ventes': json_safe(data_ventes),
        'labels_categories': json_safe(labels_cat),
        'data_categories': json_safe(data_cat),
        # Listes
        'produits_alerte': produits_alerte,
        'dernieres_factures': dernieres_factures,
        'top_produits': top_produits,
    }

    return render(request, 'dashboard/index.html', context)


# ── Rapport de stock ──────────────────────────────────────────────────────────

@login_required
def rapport_stock(request):
    entreprise = request.entreprise

    # Valeur et articles par catégorie
    par_categorie = Produit.objects.filter(
        entreprise=entreprise, actif=True
    ).values(
        'categorie__nom', 'categorie__couleur'
    ).annotate(
        nb_produits=Count('id'),
        total_articles=Sum('quantite_stock'),
        valeur=Sum(F('quantite_stock') * F('prix_achat')),
    ).order_by('-valeur')

    # Totaux globaux
    totaux = Produit.objects.filter(entreprise=entreprise, actif=True).aggregate(
        total_produits=Count('id'),
        total_articles=Sum('quantite_stock'),
        valeur_achat=Sum(F('quantite_stock') * F('prix_achat')),
        valeur_vente=Sum(F('quantite_stock') * F('prix_vente')),
    )

    # Produits en rupture
    ruptures = Produit.objects.filter(
        entreprise=entreprise, actif=True, quantite_stock=0
    ).select_related('categorie').order_by('nom')

    # Produits en alerte (stock > 0 mais <= seuil)
    alertes = Produit.objects.filter(
        entreprise=entreprise, actif=True,
        quantite_stock__gt=0,
        quantite_stock__lte=F('seuil_alerte')
    ).select_related('categorie').order_by('quantite_stock')

    # Produits les mieux stockés (valeur)
    top_valeur = Produit.objects.filter(
        entreprise=entreprise, actif=True
    ).annotate(
        valeur_calculee=F('quantite_stock') * F('prix_achat')
    ).order_by('-valeur_calculee')[:10]

    # Mouvements des 30 derniers jours par type
    debut = date.today() - timedelta(days=30)
    mouvements_par_type = MouvementStock.objects.filter(
        entreprise=entreprise,
        date_mouvement__date__gte=debut
    ).values('type_mouvement').annotate(
        nb=Count('id'),
        total_qte=Sum('quantite')
    ).order_by('-nb')

    # Données graphique valeur par catégorie
    labels_cat = []
    data_cat = []
    couleurs_cat = []
    for row in par_categorie:
        if row['valeur']:
            labels_cat.append(row['categorie__nom'] or 'Sans catégorie')
            data_cat.append(int(row['valeur']))
            couleurs_cat.append(row['categorie__couleur'] or '#6c757d')

    context = {
        'par_categorie': par_categorie,
        'totaux': totaux,
        'ruptures': ruptures,
        'alertes': alertes,
        'top_valeur': top_valeur,
        'mouvements_par_type': mouvements_par_type,
        'labels_cat': json_safe(labels_cat),
        'data_cat': json_safe(data_cat),
        'couleurs_cat': json_safe(couleurs_cat),
        'nb_ruptures': ruptures.count(),
        'nb_alertes': alertes.count(),
    }
    return render(request, 'dashboard/rapport_stock.html', context)


# ── Rapport de ventes ─────────────────────────────────────────────────────────

@login_required
def rapport_ventes(request):
    entreprise = request.entreprise
    aujourd_hui = date.today()

    periode    = request.GET.get('periode', '30')
    date_debut = request.GET.get('date_debut', '')
    date_fin   = request.GET.get('date_fin', '')

    if periode == 'today':
        debut = aujourd_hui
        fin   = aujourd_hui
        jours = 1
    elif date_debut:
        from datetime import datetime
        try:
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
        except ValueError:
            debut = aujourd_hui - timedelta(days=30)
        if date_fin:
            try:
                fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            except ValueError:
                fin = aujourd_hui
        else:
            fin = aujourd_hui
        jours = (fin - debut).days + 1
        periode = 'custom'
    else:
        jours = int(periode) if periode in ('7', '30', '90', '365') else 30
        debut = aujourd_hui - timedelta(days=jours)
        fin   = aujourd_hui

    factures_filter = dict(
        entreprise=entreprise,
        statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
    )
    if periode == 'today' or date_debut:
        factures_filter['date_emission__gte'] = debut
        factures_filter['date_emission__lte'] = fin
    else:
        factures_filter['date_emission__gte'] = debut

    factures_qs = Facture.objects.filter(**factures_filter)

    # KPIs globaux
    totaux = factures_qs.aggregate(
        ca=Sum('montant_ttc'),
        nb_factures=Count('id'),
        montant_paye=Sum('montant_paye'),
    )
    ca = totaux['ca'] or Decimal('0')
    nb_factures = totaux['nb_factures'] or 0
    panier_moyen = (ca / nb_factures) if nb_factures else Decimal('0')

    # Créances en cours
    creances = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE]
    ).aggregate(
        total=Sum(F('montant_ttc') - F('montant_paye')),
        nb=Count('id')
    )

    # Factures en retard
    en_retard = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE],
        date_echeance__lt=aujourd_hui
    ).count()

    # CA par mois (12 derniers mois)
    debut_12m = aujourd_hui - timedelta(days=365)
    ca_mensuel = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE],
        date_emission__gte=debut_12m
    ).annotate(mois=TruncMonth('date_emission')).values('mois').annotate(
        total=Sum('montant_ttc'), nb=Count('id')
    ).order_by('mois')

    labels_mois = [r['mois'].strftime('%b %Y') for r in ca_mensuel]
    data_mois = [int(r['total']) for r in ca_mensuel]

    # Top clients
    top_clients = factures_qs.values(
        'client__nom'
    ).annotate(
        ca=Sum('montant_ttc'),
        nb=Count('id')
    ).order_by('-ca')[:10]

    # Top produits vendus
    top_produits = LigneFacture.objects.filter(
        facture__entreprise=entreprise,
        facture__date_emission__gte=debut,
        facture__statut__in=[Facture.Statut.PAYEE, Facture.Statut.PARTIELLEMENT_PAYEE]
    ).values('produit__nom', 'produit__reference').annotate(
        qte=Sum('quantite'),
        ca=Sum(F('quantite') * F('prix_unitaire_ht'))
    ).order_by('-ca')[:10]

    # Répartition par mode de paiement
    par_mode = Paiement.objects.filter(
        entreprise=entreprise,
        date_paiement__gte=debut
    ).values('mode_paiement').annotate(
        total=Sum('montant'), nb=Count('id')
    ).order_by('-total')

    labels_mode = [r['mode_paiement'] for r in par_mode]
    data_mode = [int(r['total']) for r in par_mode]

    context = {
        'periode': periode,
        'jours': jours,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'ca': ca,
        'nb_factures': nb_factures,
        'panier_moyen': panier_moyen,
        'creances': creances,
        'en_retard': en_retard,
        'top_clients': top_clients,
        'top_produits': top_produits,
        'par_mode': par_mode,
        'labels_mois': json_safe(labels_mois),
        'data_mois': json_safe(data_mois),
        'labels_mode': json_safe(labels_mode),
        'data_mode': json_safe(data_mode),
    }
    return render(request, 'dashboard/rapport_ventes.html', context)


# ── Export CSV rapport de stock ───────────────────────────────────────────────

@login_required
def rapport_stock_export(request):
    import logging
    logging.getLogger('securite').info(
        f"EXPORT_CSV_STOCK user={request.user.email} "
        f"entreprise={request.entreprise} ip={request.META.get('REMOTE_ADDR')}"
    )
    entreprise = request.entreprise
    aujourd_hui = date.today()

    produits = Produit.objects.filter(
        entreprise=entreprise, actif=True
    ).select_related('categorie', 'fournisseur').order_by('categorie__nom', 'nom')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="rapport_stock_{aujourd_hui}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Référence', 'Produit', 'Catégorie', 'Fournisseur',
        'Stock actuel', 'Seuil alerte', 'Statut stock',
        'Prix achat (FCFA)', 'Prix vente (FCFA)',
        'Valeur stock achat (FCFA)', 'Valeur stock vente (FCFA)',
    ])

    for p in produits:
        if p.quantite_stock == 0:
            statut = 'Rupture'
        elif p.seuil_alerte and p.quantite_stock <= p.seuil_alerte:
            statut = 'Alerte'
        else:
            statut = 'OK'

        valeur_achat = (p.quantite_stock or 0) * (p.prix_achat or 0)
        valeur_vente = (p.quantite_stock or 0) * (p.prix_vente or 0)

        writer.writerow([
            p.reference or '',
            p.nom,
            p.categorie.nom if p.categorie else '',
            p.fournisseur.nom if p.fournisseur else '',
            p.quantite_stock or 0,
            p.seuil_alerte or 0,
            statut,
            p.prix_achat or 0,
            p.prix_vente or 0,
            round(valeur_achat, 0),
            round(valeur_vente, 0),
        ])

    # Ligne totaux
    totaux = Produit.objects.filter(entreprise=entreprise, actif=True).aggregate(
        total_articles=Sum('quantite_stock'),
        valeur_achat=Sum(F('quantite_stock') * F('prix_achat')),
        valeur_vente=Sum(F('quantite_stock') * F('prix_vente')),
    )
    writer.writerow([])
    writer.writerow([
        'TOTAL', '', '', '',
        totaux['total_articles'] or 0, '', '', '', '',
        round(totaux['valeur_achat'] or 0, 0),
        round(totaux['valeur_vente'] or 0, 0),
    ])

    return response


# ── Export CSV rapport de ventes ──────────────────────────────────────────────

@login_required
def rapport_ventes_export(request):
    import logging
    logging.getLogger('securite').info(
        f"EXPORT_CSV_VENTES user={request.user.email} "
        f"entreprise={request.entreprise} ip={request.META.get('REMOTE_ADDR')}"
    )
    entreprise = request.entreprise
    aujourd_hui = date.today()

    periode = request.GET.get('periode', '30')
    jours = int(periode) if periode in ('7', '30', '90', '365') else 30
    debut = aujourd_hui - timedelta(days=jours)

    factures = Facture.objects.filter(
        entreprise=entreprise,
        date_emission__gte=debut,
    ).select_related('client').order_by('-date_emission')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="rapport_ventes_{aujourd_hui}_({jours}j).csv"'

    writer = csv.writer(response, delimiter=';')

    # Section 1 : liste des factures
    writer.writerow([f'RAPPORT DE VENTES — {jours} derniers jours — {aujourd_hui}'])
    writer.writerow([])
    writer.writerow(['=== FACTURES ==='])
    writer.writerow([
        'Numéro', 'Date', 'Client', 'Statut',
        'Montant HT (FCFA)', 'TVA (FCFA)', 'Montant TTC (FCFA)',
        'Montant payé (FCFA)', 'Reste dû (FCFA)',
    ])

    for f in factures:
        reste = (f.montant_ttc or 0) - (f.montant_paye or 0)
        writer.writerow([
            f.numero,
            f.date_emission.strftime('%d/%m/%Y') if f.date_emission else '',
            f.client.nom if f.client else '',
            f.get_statut_display(),
            round(f.montant_ht or 0, 0),
            round((f.montant_ttc or 0) - (f.montant_ht or 0), 0),
            round(f.montant_ttc or 0, 0),
            round(f.montant_paye or 0, 0),
            round(reste, 0),
        ])

    # Section 2 : top produits
    top_produits = LigneFacture.objects.filter(
        facture__entreprise=entreprise,
        facture__date_emission__gte=debut,
    ).values('produit__nom', 'produit__reference').annotate(
        qte=Sum('quantite'),
        ca=Sum(F('quantite') * F('prix_unitaire_ht'))
    ).order_by('-ca')[:20]

    writer.writerow([])
    writer.writerow(['=== TOP PRODUITS VENDUS ==='])
    writer.writerow(['Référence', 'Produit', 'Quantité vendue', 'CA HT (FCFA)'])
    for p in top_produits:
        writer.writerow([
            p['produit__reference'] or '',
            p['produit__nom'] or '',
            p['qte'],
            round(p['ca'] or 0, 0),
        ])

    # Section 3 : modes de paiement
    par_mode = Paiement.objects.filter(
        entreprise=entreprise,
        date_paiement__gte=debut
    ).values('mode_paiement').annotate(
        total=Sum('montant'), nb=Count('id')
    ).order_by('-total')

    writer.writerow([])
    writer.writerow(['=== MODES DE PAIEMENT ==='])
    writer.writerow(['Mode', 'Nombre', 'Total (FCFA)'])
    for m in par_mode:
        writer.writerow([
            m['mode_paiement'],
            m['nb'],
            round(m['total'] or 0, 0),
        ])

    return response
