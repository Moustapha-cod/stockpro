from django.db.models import F


def alertes_stock(request):
    """Injecte les compteurs d'alertes stock dans tous les templates."""
    if not request.user.is_authenticated or request.user.is_superuser:
        return {}

    entreprise = getattr(request, 'entreprise', None)
    if not entreprise:
        return {}

    from .models import Produit

    produits_actifs = Produit.objects.filter(entreprise=entreprise, actif=True)

    nb_ruptures = produits_actifs.filter(quantite_stock=0).count()
    nb_alertes = produits_actifs.filter(
        quantite_stock__gt=0,
        quantite_stock__lte=F('seuil_alerte')
    ).count()

    return {
        'nb_ruptures': nb_ruptures,
        'nb_alertes': nb_alertes,
        'nb_alertes_total': nb_ruptures + nb_alertes,
    }
