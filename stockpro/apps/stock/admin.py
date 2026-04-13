from django.contrib import admin
from django.utils.html import format_html
from .models import Produit, ProduitPhoto, Categorie, Fournisseur, MouvementStock

# Les modèles métier (stock) ne sont pas enregistrés dans l'admin.
# La gestion du stock se fait exclusivement via l'interface applicative.
# Seul le superutilisateur accède à l'admin, pour la gestion de la plateforme uniquement.
