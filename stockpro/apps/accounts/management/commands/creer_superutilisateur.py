"""
Commande : python manage.py creer_superutilisateur

Crée un superutilisateur à partir de variables d'environnement ou de l'invite.
Utile en CI/CD et lors du premier déploiement.

Variables d'environnement supportées :
    DJANGO_SU_EMAIL     — email (identifiant de connexion)
    DJANGO_SU_USERNAME  — username Django (par défaut : partie locale de l'email)
    DJANGO_SU_PASSWORD  — mot de passe (obligatoire)
    DJANGO_SU_FIRSTNAME — prénom (optionnel)
    DJANGO_SU_LASTNAME  — nom de famille (optionnel)

Exemples :
    # Mode interactif (invite)
    python manage.py creer_superutilisateur

    # Mode non-interactif (CI/CD)
    DJANGO_SU_EMAIL=admin@monsite.sn DJANGO_SU_PASSWORD=MotDePasse123 \\
        python manage.py creer_superutilisateur --noinput
"""

import os
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Crée un superutilisateur depuis les variables d'environnement ou l'invite"

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_true',
            dest='noinput',
            help='Lit les valeurs depuis les variables d\'environnement, sans invite.',
        )

    def handle(self, *args, **options):
        noinput = options['noinput']

        if noinput:
            email    = os.environ.get('DJANGO_SU_EMAIL', '').strip()
            password = os.environ.get('DJANGO_SU_PASSWORD', '').strip()
            username = os.environ.get('DJANGO_SU_USERNAME', '').strip() or email.split('@')[0]
            prenom   = os.environ.get('DJANGO_SU_FIRSTNAME', 'Admin').strip()
            nom      = os.environ.get('DJANGO_SU_LASTNAME', '').strip()

            if not email or not password:
                raise CommandError(
                    'En mode --noinput, DJANGO_SU_EMAIL et DJANGO_SU_PASSWORD sont obligatoires.'
                )
        else:
            self.stdout.write(self.style.MIGRATE_HEADING('=== Création du superutilisateur ==='))
            email = input('Email : ').strip()
            if not email:
                raise CommandError('L\'email est obligatoire.')
            username_default = email.split('@')[0]
            username = input(f'Username [{username_default}] : ').strip() or username_default
            prenom   = input('Prénom [Admin] : ').strip() or 'Admin'
            nom      = input('Nom de famille : ').strip()
            password = getpass.getpass('Mot de passe : ')
            confirm  = getpass.getpass('Confirmez le mot de passe : ')
            if password != confirm:
                raise CommandError('Les mots de passe ne correspondent pas.')

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Un utilisateur avec l\'email « {email} » existe déjà. Aucune action.')
            )
            return

        user = User.objects.create_superuser(
            email=email,
            username=username,
            password=password,
            first_name=prenom,
            last_name=nom,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Superutilisateur créé : {user.get_full_name()} <{user.email}>'
            )
        )
