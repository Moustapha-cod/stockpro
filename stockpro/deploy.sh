#!/bin/bash
# deploy.sh — Script de déploiement StockPro SN
set -e

echo "==> Installation des dépendances..."
pip install -r requirements.txt

echo "==> Vérification des migrations versionnées..."
python manage.py makemigrations --check --dry-run

echo "==> Application des migrations..."
python manage.py migrate --noinput

echo "==> Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "==> Vérification sécurité Django..."
python manage.py check --deploy

echo "==> Démarrage Gunicorn..."
gunicorn stockpro.wsgi:application -c gunicorn.conf.py
