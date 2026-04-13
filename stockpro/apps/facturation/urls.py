from django.urls import path
from . import views

app_name = 'facturation'

urlpatterns = [
    # Clients
    path('clients/', views.client_liste, name='client_liste'),
    path('clients/nouveau/', views.client_creer, name='client_creer'),
    path('clients/<int:pk>/modifier/', views.client_modifier, name='client_modifier'),

    # Paiements
    path('paiements/', views.paiement_liste, name='paiement_liste'),
    path('paiements/<int:pk>/supprimer/', views.paiement_supprimer, name='paiement_supprimer'),

    # Créances
    path('creances/', views.creances, name='creances'),

    # Factures
    path('factures/', views.facture_liste, name='facture_liste'),
    path('factures/nouvelle/', views.facture_creer, name='facture_creer'),
    path('factures/<int:pk>/', views.facture_detail, name='facture_detail'),
    path('factures/<int:pk>/modifier/', views.facture_modifier, name='facture_modifier'),
    path('factures/<int:pk>/annuler/', views.facture_annuler, name='facture_annuler'),
    path('factures/<int:pk>/imprimer/', views.facture_imprimer, name='facture_imprimer'),
]
