from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('mon-profil/', views.mon_profil, name='mon_profil'),
    path('utilisateurs/', views.utilisateur_liste, name='utilisateur_liste'),
    path('utilisateurs/nouveau/', views.utilisateur_creer, name='utilisateur_creer'),
    path('utilisateurs/<int:pk>/modifier/', views.utilisateur_modifier, name='utilisateur_modifier'),
    path('utilisateurs/<int:pk>/toggle/', views.utilisateur_toggle_actif, name='utilisateur_toggle'),
    path('utilisateurs/<int:pk>/role/', views.utilisateur_changer_role, name='utilisateur_role'),
]
