"""
apps/stock/models.py
Gestion complète du stock : produits, catégories, fournisseurs, mouvements
"""

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.tenants.models import TenantMixin
from apps.common.validators import valider_image, chemin_upload_securise


class Categorie(TenantMixin):
    """Catégorie de pièces détachées (ex: Filtres, Freinage, Moteur…)"""

    nom = models.CharField(_('Nom'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    couleur = models.CharField(
        _('Couleur'),
        max_length=7,
        default='#6b6860',
        help_text=_('Code couleur hexadécimal pour l\'interface')
    )
    icone = models.CharField(_('Icône'), max_length=50, blank=True)
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Catégorie')
        verbose_name_plural = _('Catégories')
        ordering = ['nom']
        unique_together = [['entreprise', 'nom']]

    def __str__(self):
        return self.nom

    @property
    def nombre_produits(self):
        return self.produits.filter(actif=True).count()


class Fournisseur(TenantMixin):
    """Fournisseur de pièces détachées"""

    nom = models.CharField(_('Nom'), max_length=200)
    contact = models.CharField(_('Contact'), max_length=100, blank=True)
    telephone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    adresse = models.TextField(_('Adresse'), blank=True)
    pays = models.CharField(_('Pays'), max_length=50, default='Sénégal')
    notes = models.TextField(_('Notes'), blank=True)
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Fournisseur')
        verbose_name_plural = _('Fournisseurs')
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Produit(TenantMixin):
    """
    Pièce détachée — unité de base du stock.
    Contient toutes les informations commerciales et de suivi.
    """

    # Identification
    nom = models.CharField(_('Nom du produit'), max_length=200)
    reference = models.CharField(_('Référence'), max_length=100)
    code_barre = models.CharField(_('Code barre'), max_length=100, blank=True)
    description = models.TextField(_('Description'), blank=True)

    # Classification
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits',
        verbose_name=_('Catégorie')
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits',
        verbose_name=_('Fournisseur principal')
    )
    marque = models.CharField(_('Marque'), max_length=100, blank=True)
    modele_compatible = models.CharField(
        _('Modèle(s) compatible(s)'),
        max_length=200,
        blank=True,
        help_text=_('Ex: Toyota Corolla 2010-2020, Peugeot 206')
    )

    # Tarification
    prix_achat = models.DecimalField(
        _('Prix d\'achat (FCFA)'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        default=0
    )
    prix_vente = models.DecimalField(
        _('Prix de vente (FCFA)'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        default=0
    )

    # Stock
    quantite_stock = models.IntegerField(
        _('Quantité en stock'),
        default=0,
        validators=[MinValueValidator(0)]
    )
    seuil_alerte = models.IntegerField(
        _('Seuil d\'alerte'),
        default=5,
        help_text=_('Déclenche une alerte quand le stock descend sous ce seuil')
    )
    emplacement = models.CharField(
        _('Emplacement'),
        max_length=50,
        blank=True,
        help_text=_('Ex: Rayon A3, Étagère 2')
    )
    unite = models.CharField(_('Unité'), max_length=20, default='Pièce')

    # Image
    image = models.ImageField(_('Photo'), upload_to=chemin_upload_securise('produits'),
                              blank=True, null=True, validators=[valider_image])

    # Métadonnées
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits_crees'
    )

    class Meta:
        verbose_name = _('Produit')
        verbose_name_plural = _('Produits')
        ordering = ['nom']
        unique_together = [['entreprise', 'reference']]
        indexes = [
            models.Index(fields=['entreprise', 'reference']),
            models.Index(fields=['entreprise', 'categorie']),
            models.Index(fields=['entreprise', 'quantite_stock']),
        ]

    def __str__(self):
        return f'{self.nom} ({self.reference})'

    # ── Propriétés calculées ──────────────────────────────────────────────────

    @property
    def marge(self):
        """Marge brute en FCFA"""
        return self.prix_vente - self.prix_achat

    @property
    def taux_marge(self):
        """Taux de marge en pourcentage"""
        if self.prix_achat > 0:
            return ((self.prix_vente - self.prix_achat) / self.prix_achat) * 100
        return Decimal('0')

    @property
    def valeur_stock(self):
        """Valeur totale du stock au prix d'achat"""
        return self.quantite_stock * self.prix_achat

    @property
    def en_alerte(self):
        """True si le stock est sous le seuil d'alerte"""
        return self.quantite_stock <= self.seuil_alerte

    @property
    def en_rupture(self):
        """True si le stock est épuisé"""
        return self.quantite_stock == 0

    @property
    def statut_stock(self):
        if self.en_rupture:
            return 'rupture'
        if self.en_alerte:
            return 'alerte'
        return 'normal'


class ProduitPhoto(models.Model):
    """Photos additionnelles d'un produit (galerie multi-faces)."""

    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('Produit')
    )
    image  = models.ImageField(_('Photo'), upload_to=chemin_upload_securise('produits/photos'),
                               validators=[valider_image])
    legende = models.CharField(_('Légende'), max_length=100, blank=True,
                               help_text=_('Ex: Vue avant, Référence gravée'))
    ordre  = models.PositiveSmallIntegerField(_('Ordre'), default=0)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Photo produit')
        verbose_name_plural = _('Photos produit')
        ordering = ['ordre', 'date_ajout']

    def __str__(self):
        return f'Photo {self.pk} — {self.produit.nom}'


class MouvementStock(TenantMixin):
    """
    Historique de tous les mouvements de stock.
    Chaque entrée/sortie est tracée ici.
    """

    class TypeMouvement(models.TextChoices):
        ENTREE = 'entree', _('Entrée')
        SORTIE = 'sortie', _('Sortie')
        AJUSTEMENT = 'ajustement', _('Ajustement inventaire')
        RETOUR = 'retour', _('Retour fournisseur')
        PERTE = 'perte', _('Perte / casse')

    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='mouvements',
        verbose_name=_('Produit')
    )
    type_mouvement = models.CharField(
        _('Type'),
        max_length=20,
        choices=TypeMouvement.choices
    )
    quantite = models.IntegerField(
        _('Quantité'),
        validators=[MinValueValidator(1)]
    )
    quantite_avant = models.IntegerField(_('Qté avant mouvement'), default=0)
    quantite_apres = models.IntegerField(_('Qté après mouvement'), default=0)

    # Contexte
    prix_unitaire = models.DecimalField(
        _('Prix unitaire (FCFA)'),
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True
    )
    reference_document = models.CharField(
        _('Référence document'),
        max_length=100,
        blank=True,
        help_text=_('N° de facture, bon de commande, etc.')
    )
    motif = models.TextField(_('Motif / remarque'), blank=True)
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Fournisseur (si entrée)')
    )

    # Traçabilité
    date_mouvement = models.DateTimeField(_('Date'), default=timezone.now)
    cree_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='mouvements_crees'
    )

    class Meta:
        verbose_name = _('Mouvement de stock')
        verbose_name_plural = _('Mouvements de stock')
        ordering = ['-date_mouvement']
        indexes = [
            models.Index(fields=['entreprise', 'produit', '-date_mouvement']),
            models.Index(fields=['entreprise', 'type_mouvement', '-date_mouvement']),
        ]

    def __str__(self):
        return f'{self.get_type_mouvement_display()} — {self.produit.nom} × {self.quantite}'

    def save(self, *args, **kwargs):
        """
        Lors de la sauvegarde, met à jour le stock du produit
        et enregistre les quantités avant/après.
        """
        if not self.pk:  # Nouveau mouvement
            with transaction.atomic():
                produit = Produit.objects.select_for_update().get(pk=self.produit_id)
                self.quantite_avant = produit.quantite_stock

                if self.type_mouvement in (
                    self.TypeMouvement.ENTREE,
                    self.TypeMouvement.RETOUR
                ):
                    produit.quantite_stock += self.quantite
                elif self.type_mouvement in (
                    self.TypeMouvement.SORTIE,
                    self.TypeMouvement.PERTE
                ):
                    produit.quantite_stock = max(0, produit.quantite_stock - self.quantite)
                elif self.type_mouvement == self.TypeMouvement.AJUSTEMENT:
                    produit.quantite_stock = self.quantite  # La quantité = la nouvelle valeur

                self.quantite_apres = produit.quantite_stock
                produit.save(update_fields=['quantite_stock', 'date_modification'])
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
