"""
apps/facturation/models.py
Facturation complète : clients, factures, lignes de facture, paiements en tranches
"""

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.tenants.models import TenantMixin


class Client(TenantMixin):
    """Client acheteur (garage, mécanicien, particulier…)"""

    class TypeClient(models.TextChoices):
        PARTICULIER = 'particulier', _('Particulier')
        ENTREPRISE = 'entreprise', _('Entreprise / Garage')
        REVENDEUR = 'revendeur', _('Revendeur')

    nom = models.CharField(_('Nom / Raison sociale'), max_length=200)
    type_client = models.CharField(
        _('Type'),
        max_length=20,
        choices=TypeClient.choices,
        default=TypeClient.ENTREPRISE
    )
    contact = models.CharField(_('Nom du contact'), max_length=100, blank=True)
    telephone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    telephone2 = models.CharField(_('Téléphone 2'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    adresse = models.TextField(_('Adresse'), blank=True)
    ville = models.CharField(_('Ville'), max_length=100, blank=True, default='Dakar')
    ninea = models.CharField(_('NINEA'), max_length=50, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['nom']

    def __str__(self):
        return self.nom

    @property
    def solde_du(self):
        """Total des créances impayées sur ce client"""
        factures = self.factures.filter(
            statut__in=[Facture.Statut.EMISE, Facture.Statut.PARTIELLEMENT_PAYEE]
        )
        return sum(f.montant_restant for f in factures)

    @property
    def nombre_factures(self):
        return self.factures.count()


class Facture(TenantMixin):
    """
    Facture de vente.
    Supporte les paiements complets, partiels et en plusieurs tranches.
    """

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', _('Brouillon')
        EMISE = 'emise', _('Émise')
        PARTIELLEMENT_PAYEE = 'partielle', _('Partiellement payée')
        PAYEE = 'payee', _('Payée')
        ANNULEE = 'annulee', _('Annulée')

    class ModePaiement(models.TextChoices):
        ESPECES = 'especes', _('Espèces')
        VIREMENT = 'virement', _('Virement bancaire')
        CHEQUE = 'cheque', _('Chèque')
        WAVE = 'wave', _('Wave')
        ORANGE_MONEY = 'orange_money', _('Orange Money')
        FREE_MONEY = 'free_money', _('Free Money')
        CREDIT = 'credit', _('Crédit (paiement différé)')

    # Identification
    numero = models.CharField(_('Numéro de facture'), max_length=50)
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='factures',
        verbose_name=_('Client')
    )

    # Dates
    date_emission = models.DateField(_('Date d\'émission'), default=timezone.now)
    date_echeance = models.DateField(_('Date d\'échéance'), null=True, blank=True)

    # Montants (calculés automatiquement depuis les lignes)
    montant_ht = models.DecimalField(
        _('Montant HT'),
        max_digits=14,
        decimal_places=0,
        default=0
    )
    taux_tva = models.DecimalField(
        _('Taux TVA (%)'),
        max_digits=5,
        decimal_places=2,
        default=18.00
    )
    montant_tva = models.DecimalField(
        _('Montant TVA'),
        max_digits=14,
        decimal_places=0,
        default=0
    )
    remise_globale = models.DecimalField(
        _('Remise globale (%)'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    montant_ttc = models.DecimalField(
        _('Montant TTC'),
        max_digits=14,
        decimal_places=0,
        default=0
    )
    montant_paye = models.DecimalField(
        _('Montant payé'),
        max_digits=14,
        decimal_places=0,
        default=0
    )

    # Statut & paiement
    statut = models.CharField(
        _('Statut'),
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON
    )
    mode_paiement = models.CharField(
        _('Mode de paiement'),
        max_length=20,
        choices=ModePaiement.choices,
        default=ModePaiement.ESPECES
    )

    # Contenu
    notes = models.TextField(_('Notes / Conditions'), blank=True)
    objet = models.CharField(_('Objet'), max_length=200, blank=True)

    # Traçabilité
    cree_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='factures_creees'
    )
    date_creation    = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    supprimee_le     = models.DateTimeField(null=True, blank=True, db_index=True)
    supprimee_par    = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='factures_supprimees'
    )

    class Meta:
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')
        ordering = ['-date_emission', '-numero']
        unique_together = [['entreprise', 'numero']]
        indexes = [
            models.Index(fields=['entreprise', 'statut', '-date_emission']),
            models.Index(fields=['entreprise', 'client', '-date_emission']),
        ]

    def __str__(self):
        return f'Facture {self.numero} — {self.client.nom}'

    # ── Propriétés calculées ──────────────────────────────────────────────────

    @property
    def montant_restant(self):
        # Toujours >= 0
        return max(self.montant_ttc - self.montant_paye, 0)

    @property
    def taux_paiement(self):
        """Pourcentage payé (0 à 100)"""
        if self.montant_ttc > 0:
            taux = (self.montant_paye / self.montant_ttc) * 100
            return max(0, min(int(taux), 100))
        return 0

    @property
    def est_en_retard(self):
        from datetime import date
        return (
            self.date_echeance
            and self.date_echeance < date.today()
            and self.statut not in (self.Statut.PAYEE, self.Statut.ANNULEE)
        )

    def recalculer_totaux(self):
        """Recalcule les montants HT, TVA et TTC depuis les lignes."""
        ht = sum(ligne.montant_ht for ligne in self.lignes.all())
        from decimal import Decimal
        remise = ht * (self.remise_globale / Decimal('100'))
        ht_net = ht - remise
        tva = ht_net * (self.taux_tva / 100)
        ttc = ht_net + tva

        self.montant_ht = ht_net
        self.montant_tva = tva
        self.montant_ttc = ttc
        self.save(update_fields=['montant_ht', 'montant_tva', 'montant_ttc', 'date_modification'])

    def mettre_a_jour_statut(self):
        """Met à jour le statut en fonction des paiements reçus."""
        if self.montant_paye <= 0:
            statut = self.Statut.EMISE
        elif self.montant_paye >= self.montant_ttc:
            statut = self.Statut.PAYEE
        else:
            statut = self.Statut.PARTIELLEMENT_PAYEE

        if self.statut not in (self.Statut.BROUILLON, self.Statut.ANNULEE):
            self.statut = statut
            self.save(update_fields=['statut', 'date_modification'])

    def generer_numero(self):
        """Génère le prochain numéro de facture (FAC-YYYY-XXXX) de façon atomique."""
        from django.utils import timezone
        from django.db import transaction
        annee = timezone.now().year
        with transaction.atomic():
            derniere = Facture.objects.select_for_update().filter(
                entreprise=self.entreprise,
                numero__startswith=f'FAC-{annee}-'
            ).order_by('-id').first()

            if derniere:
                try:
                    seq = int(derniere.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1

        return f'FAC-{annee}-{seq:04d}'


class LigneFacture(models.Model):
    """Ligne d'une facture (produit + quantité + prix)"""

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Facture')
    )
    produit = models.ForeignKey(
        'stock.Produit',
        on_delete=models.PROTECT,
        related_name='lignes_facture',
        verbose_name=_('Produit')
    )
    designation = models.CharField(
        _('Désignation'),
        max_length=200,
        help_text=_('Copie du nom produit — modifiable manuellement')
    )
    reference = models.CharField(_('Référence'), max_length=100, blank=True)
    quantite = models.IntegerField(
        _('Quantité'),
        validators=[MinValueValidator(1)],
        default=1
    )
    prix_unitaire_ht = models.DecimalField(
        _('Prix unitaire HT'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    remise = models.DecimalField(
        _('Remise (%)'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    ordre = models.PositiveIntegerField(_('Ordre'), default=0)

    class Meta:
        verbose_name = _('Ligne de facture')
        verbose_name_plural = _('Lignes de facture')
        ordering = ['ordre', 'id']

    def __str__(self):
        return f'{self.designation} × {self.quantite}'

    @property
    def montant_ht(self):
        base = self.quantite * self.prix_unitaire_ht
        return base * (1 - self.remise / 100)

    def save(self, *args, **kwargs):
        # Auto-remplir depuis le produit si nouveau
        if not self.pk and not self.designation:
            self.designation = self.produit.nom
            self.reference = self.produit.reference
            self.prix_unitaire_ht = self.produit.prix_vente
        super().save(*args, **kwargs)


class Paiement(TenantMixin):
    """
    Paiement (ou tranche de paiement) sur une facture.
    Permet le suivi des paiements partiels et multiples.
    """

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name=_('Facture')
    )
    montant = models.DecimalField(
        _('Montant (FCFA)'),
        max_digits=14,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('1'))]
    )
    mode_paiement = models.CharField(
        _('Mode de paiement'),
        max_length=20,
        choices=Facture.ModePaiement.choices,
        default=Facture.ModePaiement.ESPECES
    )
    reference_paiement = models.CharField(
        _('Référence'),
        max_length=100,
        blank=True,
        help_text=_('N° de chèque, référence Wave, etc.')
    )
    date_paiement = models.DateField(_('Date de paiement'), default=timezone.now)
    notes = models.TextField(_('Notes'), blank=True)
    cree_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='paiements_enregistres'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Paiement')
        verbose_name_plural = _('Paiements')
        ordering = ['-date_paiement']

    def __str__(self):
        return f'Paiement {self.montant} FCFA — {self.facture.numero}'

    def _sync_facture(self):
        """
        Recalcule et sauvegarde montant_paye + statut de la facture (jamais négatif).
        Les paiements de type 'credit' (dette) ne sont pas considérés comme encaissés.
        """
        total_paye = self.facture.paiements.exclude(mode_paiement=Facture.ModePaiement.CREDIT).aggregate(
            total=models.Sum('montant')
        )['total'] or Decimal('0')
        # Ne jamais descendre en dessous de zéro
        self.facture.montant_paye = max(total_paye, Decimal('0'))
        self.facture.save(update_fields=['montant_paye', 'date_modification'])
        self.facture.mettre_a_jour_statut()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            self._sync_facture()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            facture = self.facture
            super().delete(*args, **kwargs)
            # Recalcule après suppression (hors dettes)
            total_paye = facture.paiements.exclude(mode_paiement=Facture.ModePaiement.CREDIT).aggregate(
                total=models.Sum('montant')
            )['total'] or Decimal('0')
            facture.montant_paye = total_paye
            facture.save(update_fields=['montant_paye', 'date_modification'])
            facture.mettre_a_jour_statut()
