from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from apps.stock.models import Produit
from apps.facturation.models import Facture, LigneFacture, Paiement
from django.contrib.auth import get_user_model

class FactureRetourPaiementTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Créer un client obligatoire
        from apps.facturation.tests.utils_entreprise import create_test_entreprise
        self.entreprise = create_test_entreprise()
        from apps.facturation.tests.utils import create_test_client
        self.client_obj = create_test_client(entreprise_id=self.entreprise.id)
        # Créer un produit
        self.produit = Produit.objects.create(
            nom='Test Produit',
            reference='REF1',
            prix_achat=Decimal('1000'),
            prix_vente=Decimal('2000'),
            quantite_stock=10,
            actif=True,
            entreprise_id=self.entreprise.id
        )
        # Créer une facture
        self.facture = Facture.objects.create(
            client=self.client_obj,
            entreprise_id=self.entreprise.id,
            montant_ttc=Decimal('4000'),
            montant_paye=Decimal('0'),
            statut=Facture.Statut.EMISE
        )
        # Ajouter une ligne de facture
        self.ligne = LigneFacture.objects.create(
            facture=self.facture,
            produit=self.produit,
            quantite=2,
            prix_unitaire_ht=Decimal('2000'),
            designation='Test Produit'
        )

    def test_paiement_partiel_et_retour(self):
        # Paiement partiel
        Paiement.objects.create(
            facture=self.facture,
            montant=Decimal('1000'),
            mode_paiement='especes',
            entreprise_id=self.entreprise.id
        )
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.montant_paye, Decimal('1000'))
        # Retour d'un produit
        self.ligne.quantite -= 1
        self.ligne.save()
        # Simuler recalcul totaux (si méthode existe)
        if hasattr(self.facture, 'recalculer_totaux'):
            self.facture.recalculer_totaux()
            self.facture.refresh_from_db()
        # Vérifier le reste à payer
        reste = self.facture.montant_ttc - self.facture.montant_paye
        print('Montant TTC:', self.facture.montant_ttc)
        print('Montant payé:', self.facture.montant_paye)
        print('Reste à payer:', reste)
        self.assertTrue(reste >= 0)
        # Vérifier l'état de la facture
        print('Statut facture:', self.facture.statut)

    def test_scenario_reel_reste_a_payer_apres_retour(self):
        # Création d'une facture de 3 plaquettes à 34 000
        self.ligne.quantite = 3
        self.ligne.prix_unitaire_ht = Decimal('34000')
        self.ligne.save()
        if hasattr(self.facture, 'recalculer_totaux'):
            self.facture.recalculer_totaux()
            self.facture.refresh_from_db()
        # Paiement de 51 000
        Paiement.objects.create(
            facture=self.facture,
            montant=Decimal('51000'),
            mode_paiement='especes',
            entreprise_id=self.entreprise.id
        )
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.montant_paye, Decimal('51000'))
        # Retour d'une plaquette
        self.ligne.quantite -= 1
        self.ligne.save()
        if hasattr(self.facture, 'recalculer_totaux'):
            self.facture.recalculer_totaux()
            self.facture.refresh_from_db()
        # Vérifications
        self.assertEqual(self.ligne.quantite, 2)
        self.assertEqual(self.facture.montant_ttc, Decimal('68000'))
        self.assertEqual(self.facture.montant_paye, Decimal('51000'))
        self.assertEqual(self.facture.montant_restant, Decimal('17000'))
