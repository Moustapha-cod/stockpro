# StockPro SN — Application de Gestion de Stock

Application web Django multi-entreprises pour la gestion de stock et la facturation, adaptée au contexte sénégalais.

---

## Architecture du projet

```
stockpro/
├── stockpro/               # Configuration Django
│   ├── settings.py         # Paramètres (PostgreSQL, apps, sécurité)
│   └── urls.py             # Routage URL principal
│
├── apps/
│   ├── tenants/            # Multi-entreprises
│   │   ├── models.py       # Entreprise + TenantMixin (isolation)
│   │   └── middleware.py   # Injection request.entreprise
│   │
│   ├── accounts/           # Authentification & rôles
│   │   ├── models.py       # User + ProfilUtilisateur (Admin/Gestionnaire/Utilisateur)
│   │   └── permissions.py  # Décorateurs et mixins d'accès
│   │
│   ├── stock/              # Gestion du stock
│   │   └── models.py       # Produit, Categorie, Fournisseur, MouvementStock
│   │
│   ├── facturation/        # Facturation & paiements
│   │   └── models.py       # Client, Facture, LigneFacture, Paiement
│   │
│   └── dashboard/          # Tableau de bord
│       └── views.py        # KPIs, graphiques, alertes
│
├── templates/              # Templates HTML
├── static/                 # CSS, JS, images
├── requirements.txt        # Dépendances Python
└── .env.example            # Variables d'environnement (modèle)
```

---

## Installation rapide

### 1. Prérequis
- Python 3.11+
- PostgreSQL 14+
- Node.js (optionnel, pour le build des assets)

### 2. Cloner et configurer
```bash
git clone <repo>
cd stockpro
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 3. Base de données PostgreSQL
```sql
-- Dans psql :
CREATE DATABASE stockpro_db;
CREATE USER stockpro_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE stockpro_db TO stockpro_user;
```

### 4. Variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

### 5. Migrations et démarrage
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver
```

---

## Modèle de données

### Isolation multi-tenant
Toutes les tables métier héritent de `TenantMixin` qui ajoute une clé étrangère vers `Entreprise`. Chaque requête est automatiquement filtrée par `request.entreprise` (injecté par le middleware).

### Rôles utilisateurs
| Rôle | Droits |
|---|---|
| **Administrateur** | Accès complet, gestion des utilisateurs |
| **Gestionnaire** | Stock + Facturation + Rapports |
| **Utilisateur** | Consultation uniquement |

### Flux de paiement facture
```
Brouillon → Émise → Partiellement payée → Payée
                  ↘ Annulée
```

---

## Prochaines étapes

- [ ] Vues et formulaires pour chaque module
- [ ] Templates HTML (basé sur le dashboard prototype)
- [ ] Génération PDF des factures (WeasyPrint)
- [ ] Export Excel des rapports (openpyxl)
- [ ] Notifications (stock faible, factures en retard)
- [ ] API REST (Django REST Framework) — optionnel
