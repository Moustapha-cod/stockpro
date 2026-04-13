#!/usr/bin/env python
import os
import sys
import django

# Ajouter le répertoire du projet au path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')

django.setup()

from apps.accounts.models import User

# Créer un nouvel utilisateur superutilisateur
user = User.objects.create_user(
    email='admin2@stockpro.sn',
    password='admin123',
    first_name='Admin',
    last_name='Test'
)
user.is_staff = True
user.is_superuser = True
user.save()

print('Nouvel utilisateur superutilisateur créé : admin2@stockpro.sn / admin123')