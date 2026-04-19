#!/bin/bash
# Script de déploiement avancé Django
# Usage : ./deploy_prod_advanced.sh

set -euo pipefail
LOGFILE="deploy_$(date +%Y%m%d_%H%M%S).log"

# 1. Aller dans le dossier du projet
cd /home/ubuntu/stockpro

# 2. Sauvegarde base SQLite (si utilisée)
if grep -q 'sqlite3' stockpro/settings.py; then
  echo "[Sauvegarde] Sauvegarde base SQLite..." | tee -a "$LOGFILE"
  cp stockpro/db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3 || true
fi

# 3. Mise à jour du code
{
  echo "[1/9] Accès au dossier du projet..."
  echo "[2/9] Mise à jour du code..."
  git pull

  # 4. Activation de l'environnement virtuel
  echo "[3/9] Activation de l'environnement virtuel..."
  source venv/bin/activate

  # 5. Installation des dépendances
  echo "[4/9] Installation des dépendances..."
  pip install -r requirements.txt

  # 6. Vérification fichiers critiques
  for f in .env stockpro/settings.py requirements.txt; do
    if [ ! -f "$f" ]; then
      echo "[ERREUR] Fichier manquant : $f" | tee -a "$LOGFILE"
      exit 1
    fi
  done

  # 7. Migrations Django
  echo "[5/9] Migrations Django..."
  cd stockpro
  python manage.py showmigrations > ../migrations_avant.txt
  python manage.py migrate | tee -a "../$LOGFILE"
  python manage.py showmigrations > ../migrations_apres.txt

  # 8. Collecte des fichiers statiques
  echo "[6/9] Collecte des fichiers statiques..."
  python manage.py collectstatic --noinput | tee -a "../$LOGFILE"
  cd ..

  # 9. Redémarrage Gunicorn
  echo "[7/9] Redémarrage de Gunicorn..."
  sudo systemctl restart gunicorn
  sleep 2
  sudo systemctl status gunicorn --no-pager | tee -a "$LOGFILE"
  sudo systemctl restart nginx
  sudo systemctl status nginx --no-pager | tee -a "$LOGFILE"

  echo "[8/9] Vérification site..."
  curl -sSf http://localhost > /dev/null && echo "Site OK" || echo "[ERREUR] Site injoignable !" | tee -a "$LOGFILE"

  echo "[9/9] Déploiement terminé avec succès !" | tee -a "$LOGFILE"
} 2>&1 | tee -a "$LOGFILE"

# Notification mail (optionnel)
# mail -s "Déploiement terminé" admin@domaine.com < "$LOGFILE"

exit 0
