"""
apps/tenants/models.py
Gestion multi-entreprises — isolation des données par tenant
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.validators import valider_image, chemin_upload_securise


class Entreprise(models.Model):
    """
    Représente une entreprise cliente (tenant).
    Chaque entreprise possède ses propres données isolées.
    """
    nom = models.CharField(_('Nom de l\'entreprise'), max_length=200)
    slug = models.SlugField(_('Identifiant unique'), unique=True)
    adresse = models.TextField(_('Adresse'), blank=True)
    telephone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    logo = models.ImageField(
        _('Logo'),
        upload_to=chemin_upload_securise('logos'),
        blank=True,
        null=True,
        validators=[valider_image],
        help_text=_('Utilisé sur les factures (recommandé : 300x100px, PNG)')
    )
    ninea = models.CharField(
        _('NINEA'),
        max_length=50,
        blank=True,
        help_text=_('Numéro d\'Identification National des Entreprises et Associations')
    )
    registre_commerce = models.CharField(_('Registre du commerce'), max_length=50, blank=True)
    devise = models.CharField(_('Devise'), max_length=10, default='FCFA')

    # Paramètres de facturation
    tva_taux = models.DecimalField(
        _('Taux TVA (%)'),
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text=_('Taux de TVA applicable au Sénégal : 18%')
    )
    mentions_facture = models.TextField(
        _('Mentions légales facture'),
        blank=True,
        help_text=_('Texte affiché en bas de chaque facture')
    )

    # Métadonnées
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(_('Date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('Dernière modification'), auto_now=True)

    class Meta:
        verbose_name = _('Entreprise')
        verbose_name_plural = _('Entreprises')
        ordering = ['nom']

    def __str__(self):
        return self.nom

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        return None


class TenantMixin(models.Model):
    """
    Mixin abstrait à hériter par tous les modèles métier.
    Assure l'isolation des données par entreprise.
    """
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        verbose_name=_('Entreprise'),
        db_index=True
    )

    class Meta:
        abstract = True
