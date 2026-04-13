from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    # Produits
    path('produits/', views.produit_liste, name='produit_liste'),
    path('produits/nouveau/', views.produit_creer, name='produit_creer'),
    path('produits/<int:pk>/modifier/', views.produit_modifier, name='produit_modifier'),
    path('produits/<int:pk>/supprimer/', views.produit_supprimer, name='produit_supprimer'),

    path('produits/photo/<int:pk>/supprimer/', views.produit_photo_supprimer, name='produit_photo_supprimer'),

    # Catégories
    path('categories/', views.categorie_liste, name='categorie_liste'),
    path('categories/nouvelle/', views.categorie_creer, name='categorie_creer'),
    path('categories/<int:pk>/modifier/', views.categorie_modifier, name='categorie_modifier'),

    # Fournisseurs
    path('fournisseurs/', views.fournisseur_liste, name='fournisseur_liste'),
    path('fournisseurs/nouveau/', views.fournisseur_creer, name='fournisseur_creer'),
    path('fournisseurs/<int:pk>/modifier/', views.fournisseur_modifier, name='fournisseur_modifier'),

    # Mouvements
    path('mouvements/', views.mouvement_liste, name='mouvement_liste'),
    path('mouvements/nouveau/', views.mouvement_creer, name='mouvement_creer'),

    # Inventaire
    path('inventaire/', views.inventaire, name='inventaire'),
    path('inventaire/export/', views.inventaire_export, name='inventaire_export'),
]
