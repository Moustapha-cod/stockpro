"""Tests des calculs financiers : CUMP, marge, taux, statut stock."""

from decimal import Decimal

from django.test import TestCase

from apps.tenants.models import Entreprise
from apps.stock.models import Produit, MouvementStock


def _entreprise(slug='calc-fin'):
    return Entreprise.objects.create(nom='Test', slug=slug, actif=True)


def _produit(entreprise, **kwargs):
    defaults = dict(
        nom='Produit Test',
        reference='REF-001',
        prix_achat=Decimal('1000'),
        prix_vente=Decimal('1500'),
        quantite_stock=0,
        actif=True,
    )
    defaults.update(kwargs)
    return Produit.objects.create(entreprise=entreprise, **defaults)


def _entree(produit, quantite, prix_unitaire, entreprise):
    return MouvementStock.objects.create(
        produit=produit,
        type_mouvement=MouvementStock.TypeMouvement.ENTREE,
        quantite=quantite,
        prix_unitaire=Decimal(str(prix_unitaire)),
        entreprise=entreprise,
    )


class CUMPTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise('cump-tests')
        self.produit = _produit(self.entreprise, prix_achat=Decimal('1000'))

    def _fresh(self):
        return Produit.objects.get(pk=self.produit.pk)

    def test_sans_mouvements_retourne_prix_achat(self):
        self.assertEqual(self.produit.cout_moyen_pondere, Decimal('1000'))

    def test_une_entree(self):
        _entree(self.produit, 10, 1200, self.entreprise)
        self.assertEqual(self._fresh().cout_moyen_pondere, Decimal('1200'))

    def test_deux_entrees_ponderees(self):
        _entree(self.produit, 10, 1000, self.entreprise)
        _entree(self.produit, 10, 2000, self.entreprise)
        # (10×1000 + 10×2000) / 20 = 1500
        self.assertEqual(self._fresh().cout_moyen_pondere, Decimal('1500'))

    def test_entree_sans_prix_ignoree(self):
        MouvementStock.objects.create(
            produit=self.produit,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE,
            quantite=5,
            prix_unitaire=None,
            entreprise=self.entreprise,
        )
        # Aucun mouvement avec prix → fallback sur prix_achat
        self.assertEqual(self._fresh().cout_moyen_pondere, Decimal('1000'))

    def test_retour_fournisseur_non_inclus_dans_cump(self):
        # Le filtre CUMP cherche ['entree', 'retour'] : 'retour_fournisseur' ne correspond pas.
        # Seules les entrées directes ('entree') entrent dans le calcul.
        _entree(self.produit, 10, 1000, self.entreprise)
        MouvementStock.objects.create(
            produit=self.produit,
            type_mouvement=MouvementStock.TypeMouvement.RETOUR_FOURNISSEUR,
            quantite=5,
            prix_unitaire=Decimal('1200'),
            entreprise=self.entreprise,
        )
        # CUMP calculé uniquement sur l'entrée à 1000
        cump = self._fresh().cout_moyen_pondere
        self.assertEqual(float(cump), 1000.0)


class MargeTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise('marge-tests')

    def test_marge_sans_mouvements(self):
        p = _produit(self.entreprise, prix_achat=Decimal('1000'), prix_vente=Decimal('1500'))
        # CUMP = prix_achat = 1000 → marge = 500
        self.assertEqual(p.marge, Decimal('500'))

    def test_marge_negative(self):
        p = _produit(self.entreprise, prix_achat=Decimal('2000'), prix_vente=Decimal('1800'))
        self.assertEqual(p.marge, Decimal('-200'))

    def test_taux_marge_50_pct(self):
        p = _produit(self.entreprise, prix_achat=Decimal('1000'), prix_vente=Decimal('1500'))
        self.assertEqual(p.taux_marge, Decimal('50'))

    def test_taux_marge_achat_zero(self):
        p = _produit(self.entreprise, prix_achat=Decimal('0'), prix_vente=Decimal('1000'))
        self.assertEqual(p.taux_marge, Decimal('0'))

    def test_valeur_stock(self):
        p = _produit(self.entreprise, prix_achat=Decimal('1000'), quantite_stock=5)
        # CUMP = 1000, valeur_stock = 5 × 1000 = 5000
        self.assertEqual(p.valeur_stock, Decimal('5000'))

    def test_valeur_stock_prix_achat(self):
        p = _produit(self.entreprise, prix_achat=Decimal('800'), quantite_stock=3)
        self.assertEqual(p.valeur_stock_prix_achat, Decimal('2400'))


class StatutStockTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise('statut-tests')

    def test_rupture(self):
        p = _produit(self.entreprise, quantite_stock=0, seuil_alerte=5)
        self.assertTrue(p.en_rupture)
        self.assertEqual(p.statut_stock, 'rupture')

    def test_alerte(self):
        p = _produit(self.entreprise, quantite_stock=3, seuil_alerte=5)
        self.assertFalse(p.en_rupture)
        self.assertTrue(p.en_alerte)
        self.assertEqual(p.statut_stock, 'alerte')

    def test_normal(self):
        p = _produit(self.entreprise, quantite_stock=10, seuil_alerte=5)
        self.assertFalse(p.en_rupture)
        self.assertFalse(p.en_alerte)
        self.assertEqual(p.statut_stock, 'normal')

    def test_exactement_au_seuil_est_alerte(self):
        p = _produit(self.entreprise, quantite_stock=5, seuil_alerte=5)
        self.assertTrue(p.en_alerte)
