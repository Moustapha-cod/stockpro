"""Utilitaires partagés entre les tests d'intégration."""

from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.accounts.models import ProfilUtilisateur
from apps.tenants.models import Entreprise
from apps.stock.models import Produit
from apps.facturation.models import Client

User = get_user_model()


def create_entreprise(slug, nom=None):
    return Entreprise.objects.create(
        nom=nom or f'Entreprise {slug}',
        slug=slug,
        actif=True,
    )


def create_user_with_entreprise(username, entreprise, password='testpass123'):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
    )
    ProfilUtilisateur.objects.create(
        utilisateur=user,
        entreprise=entreprise,
        role=ProfilUtilisateur.Role.GESTIONNAIRE,
        actif=True,
    )
    return user


def create_produit(entreprise, ref='REF-001', nom='Produit Test', **kwargs):
    defaults = dict(
        nom=nom,
        reference=ref,
        prix_achat=Decimal('1000'),
        prix_vente=Decimal('1500'),
        quantite_stock=10,
        actif=True,
    )
    defaults.update(kwargs)
    return Produit.objects.create(entreprise=entreprise, **defaults)


def create_client(entreprise, nom='Client Test'):
    return Client.objects.create(
        nom=nom,
        type_client=Client.TypeClient.PARTICULIER,
        telephone='770000000',
        entreprise=entreprise,
    )
