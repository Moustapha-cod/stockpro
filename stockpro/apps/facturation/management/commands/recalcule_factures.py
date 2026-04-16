from django.core.management.base import BaseCommand
from apps.facturation.models import Facture, LigneFacture
from apps.stock.models import Produit
from django.db import transaction

class Command(BaseCommand):
    help = "Recalcule tous les totaux, statuts de factures et stocks produits pour cohérence."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Début du recalcul des factures et stocks..."))
        with transaction.atomic():
            # Recalcul des factures
            for facture in Facture.objects.all():
                if hasattr(facture, 'recalculer_totaux'):
                    facture.recalculer_totaux()
                if hasattr(facture, 'mettre_a_jour_statut'):
                    facture.mettre_a_jour_statut()
            self.stdout.write(self.style.SUCCESS("Factures : totaux et statuts recalculés."))

            # Recalcul du stock pour chaque produit
            for produit in Produit.objects.all():
                mouvements = produit.mouvements.order_by('date_mouvement', 'id')
                stock = 0
                for m in mouvements:
                    if m.type_mouvement in [m.TypeMouvement.ENTREE, m.TypeMouvement.RETOUR_FOURNISSEUR, m.TypeMouvement.RETOUR_CLIENT]:
                        stock += m.quantite
                    elif m.type_mouvement in [m.TypeMouvement.SORTIE, m.TypeMouvement.PERTE]:
                        stock -= m.quantite
                    elif m.type_mouvement == m.TypeMouvement.AJUSTEMENT:
                        stock = m.quantite
                produit.quantite_stock = max(0, stock)
                produit.save(update_fields=["quantite_stock", "date_modification"])
            self.stdout.write(self.style.SUCCESS("Stocks produits recalculés."))
        self.stdout.write(self.style.SUCCESS("Recalcul terminé."))
