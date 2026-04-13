from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Paramètres entreprise (utilisateurs métier)
    path('parametres/', views.parametres, name='parametres'),

    # Panneau plateforme (superuser)
    path('platform/', views.platform, name='platform'),
    path('platform/nouvelle/', views.platform_creer, name='platform_creer'),
    path('platform/<int:pk>/modifier/', views.platform_modifier, name='platform_modifier'),
    path('platform/<int:pk>/toggle/', views.platform_toggle, name='platform_toggle'),
    path('platform/<int:pk>/supprimer/', views.platform_supprimer, name='platform_supprimer'),
]
