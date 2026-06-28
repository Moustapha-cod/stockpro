"""Tests des mouvements de stock : atomicité, niveaux, CUMP."""

from decimal import Decimal

from django.test import TestCase

from apps.tenants.models import Entreprise
from apps.stock.models import Produit, MouvementStock


def _entreprise(slug='mvt-tests'):
    return Entreprise.objects.create(nom='Test MVT', slug=slug, actif=True)


def _produit(entreprise, quantite_stock=10, prix_achat=Decimal('1000'), ref='REF-MVT'):
    return Produit.objects.create(
        nom='Produit MVT',
        reference=ref,
        prix_achat=prix_achat,
        prix_vente=Decimal('1500'),
        quantite_stock=quantite_stock,
        actif=True,
        entreprise=entreprise,
    )


def _mouvement(produit, type_mvt, quantite, entreprise, prix=None):
    return MouvementStock.objects.create(
        produit=produit,
        type_mouvement=type_mvt,
        quantite=quantite,
        prix_unitaire=prix,
        entreprise=entreprise,
    )


class EntreeSortieTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise()
        self.produit = _produit(self.entreprise, quantite_stock=10)

    def _stock(self):
        return Produit.objects.get(pk=self.produit.pk).quantite_stock

    def test_entree_incremente_stock(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.ENTREE, 5, self.entreprise)
        self.assertEqual(self._stock(), 15)

    def test_sortie_decremente_stock(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.SORTIE, 3, self.entreprise)
        self.assertEqual(self._stock(), 7)

    def test_sortie_ne_descent_pas_sous_zero(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.SORTIE, 50, self.entreprise)
        self.assertEqual(self._stock(), 0)

    def test_perte_decremente_stock(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.PERTE, 2, self.entreprise)
        self.assertEqual(self._stock(), 8)

    def test_retour_client_incremente_stock(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.RETOUR_CLIENT, 2, self.entreprise)
        self.assertEqual(self._stock(), 12)

    def test_retour_fournisseur_incremente_stock(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.RETOUR_FOURNISSEUR, 3, self.entreprise)
        self.assertEqual(self._stock(), 13)

    def test_ajustement_fixe_stock_exact(self):
        _mouvement(self.produit, MouvementStock.TypeMouvement.AJUSTEMENT, 25, self.entreprise)
        self.assertEqual(self._stock(), 25)


class QuantiteAvantApresTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise('qaa-tests')
        self.produit = _produit(self.entreprise, quantite_stock=10, ref='REF-QAA')

    def test_quantite_avant_apres_enregistrees(self):
        mvt = _mouvement(self.produit, MouvementStock.TypeMouvement.ENTREE, 5, self.entreprise)
        self.assertEqual(mvt.quantite_avant, 10)
        self.assertEqual(mvt.quantite_apres, 15)

    def test_quantite_avant_apres_sortie_plancher_zero(self):
        mvt = _mouvement(self.produit, MouvementStock.TypeMouvement.SORTIE, 100, self.entreprise)
        self.assertEqual(mvt.quantite_avant, 10)
        self.assertEqual(mvt.quantite_apres, 0)


class CUMPMiseAJourTest(TestCase):

    def setUp(self):
        self.entreprise = _entreprise('cump-mvt')
        self.produit = _produit(
            self.entreprise, quantite_stock=0, prix_achat=Decimal('1000'), ref='REF-CUMP'
        )

    def test_prix_achat_mis_a_jour_apres_entree(self):
        _mouvement(
            self.produit, MouvementStock.TypeMouvement.ENTREE, 10, self.entreprise,
            prix=Decimal('1200')
        )
        produit = Produit.objects.get(pk=self.produit.pk)
        # CUMP = 1200 → prix_achat mis à jour
        self.assertEqual(produit.prix_achat, Decimal('1200'))

    def test_prix_achat_pondere_apres_deux_entrees(self):
        _mouvement(
            self.produit, MouvementStock.TypeMouvement.ENTREE, 10, self.entreprise,
            prix=Decimal('1000')
        )
        _mouvement(
            self.produit, MouvementStock.TypeMouvement.ENTREE, 10, self.entreprise,
            prix=Decimal('2000')
        )
        produit = Produit.objects.get(pk=self.produit.pk)
        # CUMP = (10×1000 + 10×2000) / 20 = 1500
        self.assertEqual(produit.prix_achat, Decimal('1500'))

    def test_sortie_ne_modifie_pas_prix_achat(self):
        _mouvement(
            self.produit, MouvementStock.TypeMouvement.ENTREE, 10, self.entreprise,
            prix=Decimal('1200')
        )
        produit_apres_entree = Produit.objects.get(pk=self.produit.pk)
        prix_avant_sortie = produit_apres_entree.prix_achat

        _mouvement(produit_apres_entree, MouvementStock.TypeMouvement.SORTIE, 3, self.entreprise)
        produit_final = Produit.objects.get(pk=self.produit.pk)
        self.assertEqual(produit_final.prix_achat, prix_avant_sortie)
