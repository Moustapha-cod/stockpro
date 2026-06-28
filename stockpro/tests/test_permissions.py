"""
Tests de permissions : accès non authentifié et restrictions de rôle.

Vérifie que toutes les vues sensibles redirigent vers login quand
l'utilisateur n'est pas authentifié.
"""

from django.test import TestCase
from django.urls import reverse

from .utils import create_entreprise, create_user_with_entreprise, create_produit, create_client


URLS_PROTEGEES = [
    # Stock
    ('stock:produit_liste', None),
    ('stock:inventaire', None),
    ('stock:inventaire_export', None),
    ('stock:categorie_liste', None),
    ('stock:fournisseur_liste', None),
    ('stock:mouvement_liste', None),
    # Facturation
    ('facturation:client_liste', None),
    ('facturation:facture_liste', None),
    ('facturation:paiement_liste', None),
    ('facturation:creances', None),
]


class RedirectionNonAuthentifieTest(TestCase):
    """Toute vue protégée redirige vers /login/ quand non connecté."""

    def test_toutes_les_vues_redirigent_vers_login(self):
        for url_name, kwargs in URLS_PROTEGEES:
            with self.subTest(url=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                # Doit être une redirection (302) ou un 403
                self.assertIn(
                    response.status_code, [302, 403],
                    msg=f'{url_name} devrait rediriger non-authentifié'
                )
                if response.status_code == 302:
                    self.assertIn('login', response['Location'].lower())

    def test_api_produits_search_redirige_non_authentifie(self):
        response = self.client.get(reverse('stock:api_produits_search'), {'q': 'test'})
        self.assertIn(response.status_code, [302, 401, 403])

    def test_inventaire_export_redirige_non_authentifie(self):
        response = self.client.get(reverse('stock:inventaire_export'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'].lower())


class AccesAvecProfilTest(TestCase):
    """Un utilisateur avec un profil valide peut accéder aux vues."""

    def setUp(self):
        self.entreprise = create_entreprise('perm-tests')
        self.user = create_user_with_entreprise('perm_user', self.entreprise)
        self.produit = create_produit(self.entreprise, ref='REF-PERM')
        self.client.force_login(self.user)

    def test_produit_liste_accessible(self):
        response = self.client.get(reverse('stock:produit_liste'))
        self.assertEqual(response.status_code, 200)

    def test_inventaire_accessible(self):
        response = self.client.get(reverse('stock:inventaire'))
        self.assertEqual(response.status_code, 200)

    def test_client_liste_accessible(self):
        response = self.client.get(reverse('facturation:client_liste'))
        self.assertEqual(response.status_code, 200)

    def test_facture_liste_accessible(self):
        response = self.client.get(reverse('facturation:facture_liste'))
        self.assertEqual(response.status_code, 200)


class SuppressionProduitTest(TestCase):
    """La suppression d'un produit d'une autre entreprise doit retourner 404."""

    def setUp(self):
        self.ent_a = create_entreprise('del-a')
        self.ent_b = create_entreprise('del-b')
        self.user_a = create_user_with_entreprise('del_user_a', self.ent_a)
        self.produit_b = create_produit(self.ent_b, ref='REF-DEL-B')

    def test_supprimer_produit_autre_entreprise_retourne_404(self):
        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse('stock:produit_supprimer', args=[self.produit_b.pk])
        )
        self.assertEqual(response.status_code, 404)
        # Le produit existe toujours en base
        from apps.stock.models import Produit
        self.assertTrue(Produit.objects.filter(pk=self.produit_b.pk).exists())
