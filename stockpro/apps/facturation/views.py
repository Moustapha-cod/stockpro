"""apps/facturation/views.py — CRUD Clients, Factures, Paiements"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

import json
import logging
from .models import Client, Facture, Paiement
from django.db import models
from .forms import ClientForm, FactureForm, LigneFactureFormSet, PaiementForm
from apps.stock.models import Produit, MouvementStock
from apps.accounts.permissions import gestionnaire_requis

logger = logging.getLogger('securite')


# ── Clients ───────────────────────────────────────────────────────────────────

@login_required
def client_liste(request):
    entreprise = request.entreprise
    q = request.GET.get('q', '')
    qs = Client.objects.filter(entreprise=entreprise)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(telephone__icontains=q) | Q(email__icontains=q))
    return render(request, 'facturation/client_liste.html', {'clients': qs, 'q': q})


@login_required
def client_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.entreprise = entreprise
            client.save()
            messages.success(request, f'Client « {client.nom} » créé.')
            return redirect('facturation:client_liste')
    else:
        form = ClientForm()
    return render(request, 'facturation/client_form.html', {'form': form, 'titre': 'Nouveau client'})


@login_required
def client_modifier(request, pk):
    entreprise = request.entreprise
    client = get_object_or_404(Client, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Client « {client.nom} » modifié.')
            return redirect('facturation:client_liste')
    else:
        form = ClientForm(instance=client)
    return render(request, 'facturation/client_form.html', {'form': form, 'titre': 'Modifier le client', 'objet': client})


# ── Factures ──────────────────────────────────────────────────────────────────

@login_required
def facture_liste(request):
    entreprise = request.entreprise
    qs = Facture.objects.filter(entreprise=entreprise).select_related('client')

    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '')
    # Par défaut, masquer les factures annulées sauf si le filtre statut est utilisé
    if statut:
        qs = qs.filter(statut=statut)
    else:
        qs = qs.exclude(statut=Facture.Statut.ANNULEE)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(client__nom__icontains=q))

    context = {
        'factures': qs,
        'statut': statut,
        'q': q,
        'statuts': Facture.Statut.choices,
    }
    return render(request, 'facturation/facture_liste.html', context)


@login_required
def facture_detail(request, pk):
    entreprise = request.entreprise
    facture = get_object_or_404(Facture, pk=pk, entreprise=entreprise)
    # Exclure les lignes totalement retournées
    lignes_all = facture.lignes.select_related('produit').all()
    lignes = []
    for ligne in lignes_all:
        deja_retournee = MouvementStock.objects.filter(
            entreprise=entreprise,
            type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
            produit=ligne.produit,
            reference_document=facture.numero
        ).aggregate(total=models.Sum('quantite'))['total'] or 0
        quantite_restante = ligne.quantite - deja_retournee
        if quantite_restante > 0:
            ligne.quantite_restante = quantite_restante
            lignes.append(ligne)

    # Si la facture n'a plus aucune ligne, la laisser visible pour la traçabilité
    if not lignes and facture.statut != Facture.Statut.ANNULEE:
        # Mettre à jour le statut en 'payée' si tout est remboursé/retourné
        facture.statut = Facture.Statut.PAYEE
        facture.save(update_fields=['statut', 'date_modification'])
        messages.info(request, "Tous les produits ont été retournés/remboursés. La facture reste visible pour la traçabilité.")

    paiements = facture.paiements.order_by('date_paiement')

    if request.method == 'POST':
        # Paiement intégral rapide
        if 'payer_integral' in request.POST:
            from django.utils import timezone
            mode = request.POST.get('mode_integral', Facture.ModePaiement.ESPECES)
            if mode not in dict(Facture.ModePaiement.choices):
                messages.error(request, 'Mode de paiement invalide.')
                return redirect('facturation:facture_detail', pk=pk)
            if facture.montant_restant > 0:
                Paiement.objects.create(
                    facture=facture,
                    entreprise=entreprise,
                    montant=facture.montant_restant,
                    mode_paiement=mode,
                    date_paiement=timezone.now().date(),
                    cree_par=request.user,
                    notes='Paiement intégral',
                )
                messages.success(request, f'Facture {facture.numero} soldée intégralement.')
            return redirect('facturation:facture_detail', pk=pk)

        paiement_form = PaiementForm(request.POST, facture=facture)
        if paiement_form.is_valid():
            paiement = paiement_form.save(commit=False)
            paiement.facture = facture
            paiement.entreprise = entreprise
            paiement.cree_par = request.user
            paiement.save()
            messages.success(request, f'Paiement de {paiement.montant:,.0f} FCFA enregistré.')
            return redirect('facturation:facture_detail', pk=pk)
    else:
        paiement_form = PaiementForm(facture=facture, initial={
            'montant': facture.montant_restant,
            'mode_paiement': facture.mode_paiement,
        })

    # Historique des retours client (mouvements liés à cette facture)
    retours = MouvementStock.objects.filter(
        entreprise=entreprise,
        type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
        reference_document=facture.numero
    ).select_related('produit').order_by('-date_mouvement')

    context = {
        'facture': facture,
        'lignes': lignes,
        'paiements': paiements,
        'paiement_form': paiement_form,
        'modes': Facture.ModePaiement.choices,
        'peut_payer': facture.statut not in (Facture.Statut.PAYEE, Facture.Statut.ANNULEE) and facture.montant_ttc > 0,
        'retours': retours,
    }
    return render(request, 'facturation/facture_detail.html', context)


@login_required
def paiement_supprimer(request, pk):
    entreprise = request.entreprise
    paiement = get_object_or_404(Paiement, pk=pk, entreprise=entreprise)
    facture_pk = paiement.facture_id

    # Seuls les admins et gestionnaires peuvent supprimer un paiement
    if not request.user.is_superuser:
        if not hasattr(request.user, 'profil') or not request.user.profil.est_gestionnaire:
            messages.error(request, 'Accès réservé aux gestionnaires et administrateurs.')
            return redirect('facturation:facture_detail', pk=facture_pk)

    if request.method == 'POST':
        montant = paiement.montant
        paiement.delete()
        logger.info(
            f"PAIEMENT_SUPPRIME montant={montant} facture_id={facture_pk} "
            f"user={request.user.email} ip={request.META.get('REMOTE_ADDR')}"
        )
        messages.success(request, f'Paiement de {montant:,.0f} FCFA supprimé.')
    return redirect('facturation:facture_detail', pk=facture_pk)


@login_required
@gestionnaire_requis
def facture_creer(request):
    entreprise = request.entreprise
    if request.method == 'POST':
        form = FactureForm(request.POST, entreprise=entreprise)
        formset = LigneFactureFormSet(request.POST, form_kwargs={'entreprise': entreprise})
        if form.is_valid() and formset.is_valid():
            facture = form.save(commit=False)
            facture.entreprise = entreprise
            facture.cree_par = request.user
            facture.numero = facture.generer_numero()
            facture.save()
            formset.instance = facture
            formset.save()
            facture.recalculer_totaux()
            if facture.statut == Facture.Statut.BROUILLON:
                facture.statut = Facture.Statut.EMISE
                facture.save(update_fields=['statut'])
            # Déduire le stock pour chaque ligne de facture
            for ligne in facture.lignes.select_related('produit'):
                MouvementStock.objects.create(
                    entreprise=entreprise,
                    produit=ligne.produit,
                    type_mouvement=MouvementStock.TypeMouvement.SORTIE,
                    quantite=ligne.quantite,
                    prix_unitaire=ligne.prix_unitaire_ht,
                    reference_document=facture.numero,
                    motif=f'Vente — Facture {facture.numero}',
                    cree_par=request.user,
                )
            messages.success(request, f'Facture {facture.numero} créée.')
            return redirect('facturation:facture_detail', pk=facture.pk)
    else:
        form = FactureForm(entreprise=entreprise)
        formset = LigneFactureFormSet(form_kwargs={'entreprise': entreprise})

    produits = Produit.objects.filter(entreprise=entreprise, actif=True).values('id', 'nom', 'prix_vente')
    produits_data = {str(p['id']): {'nom': p['nom'], 'prix': str(p['prix_vente'])} for p in produits}

    return render(request, 'facturation/facture_form.html', {
        'form': form,
        'formset': formset,
        'titre': 'Nouvelle facture',
        'produits_data': produits_data,
    })


@login_required
@gestionnaire_requis
def facture_modifier(request, pk):
    entreprise = request.entreprise
    facture = get_object_or_404(Facture, pk=pk, entreprise=entreprise)

    if facture.statut == Facture.Statut.ANNULEE:
        messages.error(request, 'Impossible de modifier une facture annulée.')
        return redirect('facturation:facture_detail', pk=pk)

    if request.method == 'POST':
        form = FactureForm(request.POST, instance=facture, entreprise=entreprise)
        formset = LigneFactureFormSet(request.POST, instance=facture, form_kwargs={'entreprise': entreprise})
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            facture.recalculer_totaux()
            messages.success(request, f'Facture {facture.numero} modifiée.')
            return redirect('facturation:facture_detail', pk=facture.pk)
    else:
        form = FactureForm(instance=facture, entreprise=entreprise)
        formset = LigneFactureFormSet(instance=facture, form_kwargs={'entreprise': entreprise})

    produits = Produit.objects.filter(entreprise=entreprise, actif=True).values('id', 'nom', 'prix_vente')
    produits_data = {str(p['id']): {'nom': p['nom'], 'prix': str(p['prix_vente'])} for p in produits}

    return render(request, 'facturation/facture_form.html', {
        'form': form,
        'formset': formset,
        'titre': f'Modifier {facture.numero}',
        'facture': facture,
        'produits_data': produits_data,
    })


@login_required
def paiement_liste(request):
    from datetime import date, timedelta
    from decimal import Decimal
    entreprise = request.entreprise

    qs = Paiement.objects.filter(entreprise=entreprise).select_related('facture', 'facture__client', 'cree_par')

    # Filtres
    mode        = request.GET.get('mode', '')
    periode     = request.GET.get('periode', '30')
    date_debut  = request.GET.get('date_debut', '')
    date_fin    = request.GET.get('date_fin', '')

    if mode:
        qs = qs.filter(mode_paiement=mode)

    if date_debut:
        qs = qs.filter(date_paiement__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_paiement__lte=date_fin)
    elif periode == 'today':
        qs = qs.filter(date_paiement=date.today())
    elif periode:
        jours = int(periode) if periode in ('7', '30', '90', '365') else 30
        qs = qs.filter(date_paiement__gte=date.today() - timedelta(days=jours))
        if date_fin:
            qs = qs.filter(date_paiement__lte=date_fin)

    # KPIs
    totaux = qs.aggregate(
        total=Sum('montant'),
        nb=Count('id'),
    )
    total_encaisse = totaux['total'] or Decimal('0')
    nb_paiements   = totaux['nb'] or 0

    # Total dettes (mode crédit)
    total_dettes = qs.filter(mode_paiement='credit').aggregate(t=Sum('montant'))['t'] or Decimal('0')
    total_reel   = total_encaisse - total_dettes

    # Répartition par mode
    par_mode = qs.values('mode_paiement').annotate(total=Sum('montant'), nb=Count('id')).order_by('-total')

    context = {
        'paiements': qs.order_by('-date_paiement')[:300],
        'mode': mode,
        'modes': Facture.ModePaiement.choices,
        'periode': periode,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_encaisse': total_encaisse,
        'total_reel': total_reel,
        'total_dettes': total_dettes,
        'nb_paiements': nb_paiements,
        'par_mode': par_mode,
    }
    return render(request, 'facturation/paiement_liste.html', context)


@login_required
def creances(request):
    from decimal import Decimal
    entreprise = request.entreprise

    # Factures non soldées
    factures_qs = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE]
    ).select_related('client').order_by('client__nom', 'date_echeance')

    # Filtres
    client_id  = request.GET.get('client', '')
    retard     = request.GET.get('retard', '')
    if client_id:
        factures_qs = factures_qs.filter(client_id=client_id)
    if retard == '1':
        from datetime import date
        factures_qs = factures_qs.filter(date_echeance__lt=date.today())

    # KPIs globaux
    totaux = factures_qs.aggregate(
        total_ttc=Sum('montant_ttc'),
        total_paye=Sum('montant_paye'),
        nb=Count('id'),
    )
    total_du    = (totaux['total_ttc'] or Decimal('0')) - (totaux['total_paye'] or Decimal('0'))
    nb_factures = totaux['nb'] or 0

    from datetime import date as _date
    nb_retard = Facture.objects.filter(
        entreprise=entreprise,
        statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE],
        date_echeance__lt=_date.today()
    ).count()

    # Regroupement par client
    clients_qs = Client.objects.filter(entreprise=entreprise).order_by('nom')

    context = {
        'factures': factures_qs,
        'clients': clients_qs,
        'client_id': client_id,
        'retard': retard,
        'total_du': total_du,
        'nb_factures': nb_factures,
        'nb_retard': nb_retard,
        'modes': Facture.ModePaiement.choices,
    }
    return render(request, 'facturation/creances.html', context)


@login_required
def facture_imprimer(request, pk):
    entreprise = request.entreprise
    facture = get_object_or_404(Facture, pk=pk, entreprise=entreprise)
    lignes = facture.lignes.select_related('produit').all()
    paiements = facture.paiements.order_by('date_paiement')
    return render(request, 'facturation/facture_imprimer.html', {
        'facture': facture,
        'lignes': lignes,
        'paiements': paiements,
        'entreprise': entreprise,
    })


@login_required
@gestionnaire_requis
def facture_annuler(request, pk):
    entreprise = request.entreprise
    facture = get_object_or_404(Facture, pk=pk, entreprise=entreprise)
    if request.method == 'POST':
        from django.utils import timezone
        import logging
        # Pour chaque ligne, calculer la quantité non encore retournée et recréditer le stock
        lignes = facture.lignes.select_related('produit').all()
        for ligne in lignes:
            deja_retournee = MouvementStock.objects.filter(
                entreprise=entreprise,
                type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
                produit=ligne.produit,
                reference_document=facture.numero
            ).aggregate(total=models.Sum('quantite'))['total'] or 0
            quantite_a_retourner = ligne.quantite - deja_retournee
            if quantite_a_retourner > 0:
                MouvementStock.objects.create(
                    entreprise=entreprise,
                    produit=ligne.produit,
                    type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
                    quantite=quantite_a_retourner,
                    prix_unitaire=ligne.prix_unitaire_ht,
                    reference_document=facture.numero,
                    motif='Annulation facture',
                    cree_par=request.user
                )
        facture.statut       = Facture.Statut.ANNULEE
        facture.supprimee_le  = timezone.now()
        facture.supprimee_par = request.user
        facture.save(update_fields=['statut', 'supprimee_le', 'supprimee_par', 'date_modification'])
        logging.getLogger('securite').info(
            f"FACTURE_ANNULEE numero={facture.numero} user={request.user.email} "
            f"entreprise={entreprise} ip={request.META.get('REMOTE_ADDR')}"
        )
        messages.success(request, f'Facture {facture.numero} annulée. Stock remis à jour.')
        return redirect('facturation:facture_liste')
    return render(request, 'facturation/facture_annuler.html', {'facture': facture})


from django import forms
from django.forms import formset_factory

class RetourProduitForm(forms.Form):
    produit = forms.ChoiceField(label="Produit", required=True)
    quantite_retour = forms.IntegerField(label="Quantité à retourner", min_value=1)

    def __init__(self, *args, produits_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if produits_choices is not None:
            self.fields['produit'].choices = produits_choices

@login_required
@gestionnaire_requis
def facture_retour_produit(request, pk):
    entreprise = request.entreprise
    facture = get_object_or_404(Facture, pk=pk, entreprise=entreprise)
    lignes = list(facture.lignes.select_related('produit').all())
    produits_choices = [(str(l.id), f"{l.produit.nom} (Qté facturée: {l.quantite})") for l in lignes]

    # Crée une sous-classe pour injecter les choix produits
    class RetourProduitFormWithChoices(RetourProduitForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, produits_choices=produits_choices, **kwargs)

    RetourFormSet = formset_factory(RetourProduitFormWithChoices, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = RetourFormSet(request.POST)
        if formset.is_valid():
            retours = []
            montant_total_rembourse = 0
            for form in formset:
                if form.cleaned_data.get('DELETE'):
                    continue
                # Ignore les formulaires incomplets
                if 'produit' not in form.cleaned_data or 'quantite_retour' not in form.cleaned_data:
                    continue
                try:
                    ligne_id = int(form.cleaned_data['produit'])
                    quantite_retour = form.cleaned_data['quantite_retour']
                except (KeyError, ValueError, TypeError):
                    continue
                ligne = next((l for l in lignes if l.id == ligne_id), None)
                if not ligne or quantite_retour <= 0:
                    continue
                # Calcul de la quantité déjà retournée pour cette ligne
                deja_retournee = MouvementStock.objects.filter(
                    entreprise=entreprise,
                    type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
                    produit=ligne.produit,
                    reference_document=facture.numero
                ).aggregate(total=models.Sum('quantite'))['total'] or 0
                max_retour = ligne.quantite - deja_retournee
                if quantite_retour > max_retour:
                    messages.warning(request, f"Impossible de retourner plus que la quantité restante pour {ligne.produit.nom} (déjà retourné : {deja_retournee}, facturé : {ligne.quantite})")
                    continue
                # Met à jour la quantité de la ligne de facture
                ligne.quantite -= quantite_retour
                if ligne.quantite < 0:
                    ligne.quantite = 0
                ligne.save(update_fields=["quantite"])
                MouvementStock.objects.create(
                    entreprise=entreprise,
                    produit=ligne.produit,
                    type_mouvement=MouvementStock.TypeMouvement.RETOUR_CLIENT,
                    quantite=quantite_retour,
                    prix_unitaire=ligne.prix_unitaire_ht,
                    reference_document=facture.numero,
                    motif=f'Retour client sur facture {facture.numero}',
                    cree_par=request.user,
                )
                montant_total_rembourse += quantite_retour * ligne.prix_unitaire_ht
                retours.append((ligne, quantite_retour))
            if retours:
                # Recalcule tous les totaux de la facture sur la base des nouvelles quantités
                facture.recalculer_totaux()

                # Ne pas créer de paiement négatif automatique : le montant_paye reste inchangé
                # Si reste à payer < 0, afficher un message d'avoir/trop-perçu
                reste_a_payer = facture.montant_ttc - facture.montant_paye
                if reste_a_payer < 0:
                    messages.info(request, f"Trop-perçu de {-reste_a_payer:,.0f} FCFA : un avoir ou remboursement est à prévoir.")
                # Vérifie si tous les produits sont totalement retournés
                lignes_restantes = 0
                for ligne in facture.lignes.all():
                    if ligne.quantite > 0:
                        lignes_restantes += 1
                if lignes_restantes == 0:
                    # Annule la facture et met tous les montants à zéro
                    facture.statut = Facture.Statut.ANNULEE
                    facture.montant_ht = 0
                    facture.montant_tva = 0
                    facture.montant_ttc = 0
                    facture.save(update_fields=['statut', 'montant_ht', 'montant_tva', 'montant_ttc', 'date_modification'])
                    messages.success(request, "Tous les produits ont été retournés : la facture est annulée.")
                    return redirect('facturation:facture_detail', pk=pk)
                else:
                    facture.save(update_fields=['montant_ht', 'montant_tva', 'montant_ttc', 'date_modification'])
                    if hasattr(facture, 'mettre_a_jour_statut'):
                        facture.mettre_a_jour_statut()
                    messages.success(request, f'Retour produit enregistré. Montant TTC diminué de {montant_total_rembourse:,.0f} FCFA.')
                    return redirect('facturation:facture_detail', pk=pk)
            else:
                messages.warning(request, 'Aucun produit sélectionné pour le retour.')
    else:
        formset = RetourFormSet()

    context = {
        'facture': facture,
        'formset': formset,
    }
    return render(request, 'facturation/facture_retour.html', context)
