# Script de déploiement automatique Django (à lancer depuis le serveur)
# Usage : ./deploy_prod.sh

set -e

# 1. Aller dans le dossier du projet
echo "[1/7] Accès au dossier du projet..."
cd /home/ubuntu/stockpro

# 2. Mettre à jour le code (git pull)
echo "[2/7] Mise à jour du code..."
git pull

# 3. Activer l'environnement virtuel
echo "[3/7] Activation de l'environnement virtuel..."
source venv/bin/activate

# 4. Installer les dépendances si besoin
echo "[4/7] Installation des dépendances..."
pip install -r requirements.txt

# 5. Appliquer les migrations
echo "[5/7] Migrations Django..."
cd stockpro
python manage.py migrate

# 6. Collecter les fichiers statiques
echo "[6/7] Collecte des fichiers statiques..."
python manage.py collectstatic --noinput
cd ..

# 7. Redémarrer Gunicorn
echo "[7/7] Redémarrage de Gunicorn..."
sudo systemctl restart gunicorn

echo "Déploiement terminé avec succès !"
#!/bin/bash
# Script de déploiement automatique des fichiers de config prod
# À lancer depuis la racine du projet local

# Variables
SERVER_USER=ubuntu
SERVER_IP=57.128.159.233

# Envoi des fichiers
scp deploy/nginx.conf $SERVER_USER@$SERVER_IP:/tmp/nginx.conf
scp deploy/gunicorn.service $SERVER_USER@$SERVER_IP:/tmp/gunicorn.service

echo "Connexion SSH et installation côté serveur..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/stockpro
sudo ln -sf /etc/nginx/sites-available/stockpro /etc/nginx/sites-enabled/stockpro
sudo mv /tmp/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl restart nginx
echo "Déploiement terminé."
ENDSSH
