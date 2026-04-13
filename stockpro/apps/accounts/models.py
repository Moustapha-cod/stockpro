"""
apps/accounts/models.py
Utilisateurs personnalisés avec rôles et rattachement entreprise
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.validators import valider_image, chemin_upload_securise


class User(AbstractUser):
    """Utilisateur étendu — remplace le modèle Django par défaut."""

    email = models.EmailField(_('Adresse email'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}>'

    @property
    def nom_complet(self):
        return self.get_full_name() or self.email

    @property
    def initiales(self):
        parts = self.get_full_name().split()
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[-1][0]}'.upper()
        return self.email[:2].upper()


class ProfilUtilisateur(models.Model):
    """Profil étendu : rôle, entreprise, préférences."""

    class Role(models.TextChoices):
        ADMINISTRATEUR = 'admin', _('Administrateur')
        GESTIONNAIRE = 'gestionnaire', _('Gestionnaire')
        UTILISATEUR = 'utilisateur', _('Utilisateur')

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil',
        verbose_name=_('Utilisateur')
    )
    entreprise = models.ForeignKey(
        'tenants.Entreprise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membres',
        verbose_name=_('Entreprise')
    )
    role = models.CharField(
        _('Rôle'),
        max_length=20,
        choices=Role.choices,
        default=Role.UTILISATEUR
    )
    telephone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    avatar = models.ImageField(_('Avatar'), upload_to=chemin_upload_securise('avatars'),
                               blank=True, null=True, validators=[valider_image])
    actif = models.BooleanField(_('Actif'), default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    derniere_connexion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Profil utilisateur')
        verbose_name_plural = _('Profils utilisateurs')

    def __str__(self):
        return f'{self.utilisateur.nom_complet} — {self.get_role_display()}'

    # ── Permissions par rôle ──────────────────────────────────────────────────

    @property
    def est_admin(self):
        return self.role == self.Role.ADMINISTRATEUR

    @property
    def est_gestionnaire(self):
        return self.role in (self.Role.ADMINISTRATEUR, self.Role.GESTIONNAIRE)

    @property
    def peut_modifier_stock(self):
        return self.role in (self.Role.ADMINISTRATEUR, self.Role.GESTIONNAIRE)

    @property
    def peut_creer_facture(self):
        return self.role in (self.Role.ADMINISTRATEUR, self.Role.GESTIONNAIRE)

    @property
    def peut_voir_rapports(self):
        return self.role in (self.Role.ADMINISTRATEUR, self.Role.GESTIONNAIRE)

    @property
    def peut_gerer_utilisateurs(self):
        return self.role == self.Role.ADMINISTRATEUR
