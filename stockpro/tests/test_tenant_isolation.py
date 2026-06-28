"""
Tests d'isolation tenant.

Garantit que chaque entreprise voit uniquement ses propres données,
même quand plusieurs entreprises coexistent dans la base de données.
"""

from django.test import TestCase
from django.urls import reverse

from .utils import (
    create_entreprise,
    create_user_with_entreprise,
    create_produit,
    create_client,
)


class ProduitIsolationTest(TestCase):
    """Les produits d'entreprise B ne doivent pas être visibles pour entreprise A."""

    def setUp(self):
        self.ent_a = create_entreprise('ent-a')
        self.ent_b = create_entreprise('ent-b')
        self.user_a = create_user_with_entreprise('user_a', self.ent_a)
        self.user_b = create_user_with_entreprise('user_b', self.ent_b)

        self.produit_a = create_produit(self.ent_a, ref='REF-A', nom='Produit A')
        self.produit_b = create_produit(self.ent_b, ref='REF-B', nom='Produit B')

    def test_produit_liste_ne_montre_que_ses_propres_produits(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('stock:produit_liste'))
        self.assertEqual(response.status_code, 200)
        produits = list(response.context['produits'])
        refs = [p.reference for p in produits]
        self.assertIn('REF-A', refs)
        self.assertNotIn('REF-B', refs)

    def test_api_produits_search_limite_au_tenant(self):
        self.client.force_login(self.user_a)
        response = self.client.get(
            reverse('stock:api_produits_search'), {'q': 'Produit'}
        )
        self.assertEqual(response.status_code, 200)
        # L'API retourne {'results': [{'value': pk, 'text': 'Nom [Ref]', ...}]}
        results = response.json()['results']
        texts = ' '.join(r['text'] for r in results)
        self.assertIn('Produit A', texts)
        self.assertNotIn('Produit B', texts)

    def test_inventaire_export_limite_au_tenant(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('stock:inventaire_export'))
        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content).decode('utf-8-sig')
        self.assertIn('REF-A', content)
        self.assertNotIn('REF-B', content)

    def test_produit_detail_autre_entreprise_retourne_404(self):
        self.client.force_login(self.user_a)
        # Tenter d'accéder au produit de ent_b via l'URL de modification
        response = self.client.get(
            reverse('stock:produit_modifier', args=[self.produit_b.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_supprimer_photo_autre_entreprise_retourne_404(self):
        from apps.stock.models import ProduitPhoto
        import os
        photo_b = ProduitPhoto.objects.create(
            produit=self.produit_b,
            image='produits/test.jpg',
        )
        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse('stock:produit_photo_supprimer', args=[photo_b.pk])
        )
        self.assertEqual(response.status_code, 404)


class ClientIsolationTest(TestCase):
    """Les clients d'entreprise B ne doivent pas être visibles pour entreprise A."""

    def setUp(self):
        self.ent_a = create_entreprise('cli-a')
        self.ent_b = create_entreprise('cli-b')
        self.user_a = create_user_with_entreprise('cli_user_a', self.ent_a)

        self.client_a = create_client(self.ent_a, nom='Client Ent A')
        self.client_b = create_client(self.ent_b, nom='Client Ent B')

    def test_client_liste_ne_montre_que_ses_propres_clients(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('facturation:client_liste'))
        self.assertEqual(response.status_code, 200)
        clients = list(response.context['clients'])
        noms = [c.nom for c in clients]
        self.assertIn('Client Ent A', noms)
        self.assertNotIn('Client Ent B', noms)

    def test_facture_liste_ne_montre_que_ses_propres_factures(self):
        from decimal import Decimal
        from apps.facturation.models import Facture
        facture_a = Facture.objects.create(
            client=self.client_a,
            entreprise=self.ent_a,
            montant_ttc=Decimal('10000'),
            montant_paye=Decimal('0'),
            statut=Facture.Statut.EMISE,
            numero='FAC-2026-0001',
        )
        facture_b = Facture.objects.create(
            client=self.client_b,
            entreprise=self.ent_b,
            montant_ttc=Decimal('20000'),
            montant_paye=Decimal('0'),
            statut=Facture.Statut.EMISE,
            numero='FAC-2026-0002',
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('facturation:facture_liste'))
        self.assertEqual(response.status_code, 200)
        factures = list(response.context['factures'])
        numeros = [f.numero for f in factures]
        self.assertIn('FAC-2026-0001', numeros)
        self.assertNotIn('FAC-2026-0002', numeros)
