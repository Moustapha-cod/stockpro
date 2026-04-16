from django.core.management.base import BaseCommand
from apps.stock.models import Produit, MouvementStock
from django.db.models import Max

class Command(BaseCommand):
    help = "Vérifie la cohérence entre la quantité réelle du produit et la dernière valeur de 'quantite_apres' dans les mouvements."

    def handle(self, *args, **options):
        erreurs = []
        for produit in Produit.objects.all():
            dernier_mouvement = (
                MouvementStock.objects.filter(produit=produit)
                .order_by('-date_mouvement', '-id')
                .first()
            )
            if dernier_mouvement:
                if produit.quantite_stock != dernier_mouvement.quantite_apres:
                    erreurs.append(
                        f"Produit: {produit.nom} ({produit.reference}) | Stock: {produit.quantite_stock} | Dernier mouvement: {dernier_mouvement.quantite_apres} | Mouvement ID: {dernier_mouvement.id}"
                    )
        if erreurs:
            self.stdout.write(self.style.ERROR("Incohérences détectées :"))
            for err in erreurs:
                self.stdout.write(self.style.ERROR(err))
        else:
            self.stdout.write(self.style.SUCCESS("Aucune incohérence détectée. Toutes les quantités sont cohérentes."))
