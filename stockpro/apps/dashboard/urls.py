from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('rapport-stock/', views.rapport_stock, name='rapport_stock'),
    path('rapport-ventes/', views.rapport_ventes, name='rapport_ventes'),
    path('rapport-stock/export/', views.rapport_stock_export, name='rapport_stock_export'),
    path('rapport-ventes/export/', views.rapport_ventes_export, name='rapport_ventes_export'),
]
