#!/usr/bin/env python
import os
import django
import sys

# Configuration Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()

from apps.tenants.models import Entreprise
from apps.accounts.models import User, ProfilUtilisateur

def create_test_data():
    # Créer une entreprise
    entreprise, created = Entreprise.objects.get_or_create(
        nom='StockPro Demo',
        defaults={
            'slug': 'stockpro-demo',
            'email': 'demo@stockpro.sn',
            'telephone': '+221 77 123 45 67',
            'adresse': 'Dakar, Sénégal'
        }
    )
    print(f"Entreprise créée: {entreprise.nom}")

    # Créer un superutilisateur
    user, created = User.objects.get_or_create(
        email='admin@stockpro.sn',
        defaults={
            'username': 'admin',
            'first_name': 'Administrateur',
            'last_name': 'StockPro',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
        print(f"Superutilisateur créé: {user.email}")

        # Créer le profil utilisateur
        profil, created = ProfilUtilisateur.objects.get_or_create(
            utilisateur=user,
            defaults={
                'entreprise': entreprise,
                'role': 'admin'
            }
        )
        print(f"Profil créé pour {user.email}")
    else:
        print(f"Utilisateur existe déjà: {user.email}")

if __name__ == '__main__':
    create_test_data()
    print("Données de test créées avec succès!")