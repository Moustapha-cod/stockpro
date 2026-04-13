"""
StockPro SN — Configuration principale Django
Application de gestion de stock multi-entreprises
"""

from pathlib import Path
import os
from decouple import config, UndefinedValueError

# Créer les répertoires nécessaires automatiquement
os.makedirs(Path(__file__).resolve().parent.parent / 'logs', exist_ok=True)
os.makedirs(Path(__file__).resolve().parent.parent / 'media', exist_ok=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Sécurité ────────────────────────────────────────────────────────────────
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = [
    host.strip()
    for host in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
    if host.strip()
]

try:
    SECRET_KEY = config('SECRET_KEY')
except UndefinedValueError:
    SECRET_KEY = ''

if SECRET_KEY in ('change-this-in-production', '', 'your-secret-key'):
    if DEBUG:
        # En développement local, génère une clé temporaire NON persistante.
        import secrets
        SECRET_KEY = secrets.token_urlsafe(50)
    else:
        raise ValueError(
            "SECRET_KEY doit être définie avec une vraie valeur en production."
        )

# ─── Applications ─────────────────────────────────────────────────────────────
DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'widget_tweaks',
    'axes',
]

LOCAL_APPS = [
    'apps.tenants',       # Gestion multi-entreprises
    'apps.accounts',      # Authentification & rôles
    'apps.stock',         # Produits, catégories, fournisseurs, mouvements
    'apps.facturation',   # Factures, paiements
    'apps.dashboard',     # Tableau de bord & rapports
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'apps.common.middleware.SecurityHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',              # Rate limiting login
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.tenants.middleware.TenantMiddleware',    # Isolation entreprise
]

ROOT_URLCONF = 'stockpro.urls'
WSGI_APPLICATION = 'stockpro.wsgi.application'

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.tenants.context_processors.current_tenant',  # Injecte l'entreprise courante
            ],
        },
    },
]

# ─── Base de données ──────────────────────────────────────────────────────────
# SQLite en développement, PostgreSQL en production via DATABASE_URL
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    except ImportError:
        raise ImportError(
            "dj-database-url est requis quand DATABASE_URL est défini. "
            "Installez-le : pip install dj-database-url"
        )
else:
    DATABASES = {
        'default': {
            'ENGINE':   config('DB_ENGINE',   default='django.db.backends.sqlite3'),
            'NAME':     config('DB_NAME',     default=str(BASE_DIR / 'db.sqlite3')),
            'USER':     config('DB_USER',     default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='5432'),
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
        }
    }

if not DEBUG and DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    raise ValueError(
        "SQLite n'est pas autorisee en production. Configurez PostgreSQL via DATABASE_URL "
        "ou les variables DB_* dans l'environnement."
    )

# ─── Authentification ─────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'accounts:login'

# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-sn'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fr', 'Français'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# ─── Fichiers statiques & médias ──────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Crispy Forms ─────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ─── Pagination ───────────────────────────────────────────────────────────────
DEFAULT_PAGINATION_SIZE = 25

# ─── Devise locale ───────────────────────────────────────────────────────────
CURRENCY = 'FCFA'
CURRENCY_SYMBOL = 'F'

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@stockpro.sn')

# ─── Clé primaire par défaut ──────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Limites upload fichiers ──────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 Mo max par requête POST
FILE_UPLOAD_MAX_MEMORY_SIZE = 5  * 1024 * 1024   # 5 Mo — fichiers en mémoire au-delà → disque

# ─── Sécurité des cookies et sessions ────────────────────────────────────────
SESSION_COOKIE_HTTPONLY  = True          # Inaccessible depuis JavaScript
SESSION_COOKIE_SAMESITE  = 'Lax'        # Protège contre CSRF cross-site
SESSION_COOKIE_AGE       = 60 * 60 * 8  # Expiration : 8 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# En production uniquement (HTTPS obligatoire)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE    = True

# ─── Logging sécurité ────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'securite': {
            'format': '[{asctime}] {levelname} {name} — {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'fichier_securite': {
            'class':     'logging.handlers.RotatingFileHandler',
            'filename':  str(BASE_DIR / 'logs' / 'securite.log'),
            'maxBytes':  5 * 1024 * 1024,  # 5 Mo max par fichier
            'backupCount': 5,
            'formatter': 'securite',
            'encoding':  'utf-8',
        },
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'securite',
        },
    },
    'loggers': {
        'securite': {
            'handlers':  ['fichier_securite', 'console'],
            'level':     'INFO',
            'propagate': False,
        },
        'axes': {
            'handlers':  ['fichier_securite'],
            'level':     'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers':  ['fichier_securite'],
            'level':     'WARNING',
            'propagate': False,
        },
    },
}

# ─── django-axes — Protection brute-force ────────────────────────────────────
AXES_FAILURE_LIMIT        = 5          # Blocage après 5 échecs
AXES_COOLOFF_TIME         = 1          # Déblocage automatique après 1 heure
AXES_LOCKOUT_CALLABLE     = None       # Utilise le comportement par défaut
AXES_RESET_ON_SUCCESS     = True       # Réinitialise le compteur à la connexion réussie
AXES_LOCKOUT_PARAMETERS   = ['username', 'ip_address']  # Bloque par IP + username
AXES_ENABLE_ADMIN         = False      # Pas d'interface axes dans l'admin

# ─── Jazzmin — Admin UI ───────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title":    "StockPro SN",
    "site_header":   "StockPro SN",
    "site_brand":    "StockPro SN",
    "welcome_sign":  "Bienvenue dans l'administration StockPro SN",
    "copyright":     "StockPro SN — Gestion de stock automobile",

    "site_icon":  None,
    "site_logo":  None,

    "search_model": ["accounts.User", "stock.Produit", "facturation.Facture"],

    "user_avatar": None,

    "topmenu_links": [
        {"name": "← Retour application", "url": "/entreprise/platform/", "new_window": False},
        {"name": "Entreprises",           "url": "/entreprise/platform/", "new_window": False},
        {"name": "Utilisateurs",          "url": "/utilisateurs/",        "new_window": False},
    ],

    "usermenu_links": [
        {"name": "Mon profil", "url": "admin:index",       "icon": "fas fa-user"},
        {"name": "Application","url": "/dashboard/",       "icon": "fas fa-home", "new_window": False},
    ],

    "show_sidebar": True,
    "navigation_expanded": True,

    "order_with_respect_to": [
        "tenants", "accounts", "auth",
    ],

    "hide_apps": ["stock", "facturation"],

    "icons": {
        "accounts":                   "fas fa-users",
        "accounts.User":              "fas fa-user",
        "accounts.ProfilUtilisateur": "fas fa-id-card",
        "tenants":                    "fas fa-building",
        "tenants.Entreprise":         "fas fa-building",
        "stock":                      "fas fa-boxes",
        "stock.Produit":              "fas fa-box-open",
        "stock.ProduitPhoto":         "fas fa-images",
        "stock.Categorie":            "fas fa-tags",
        "stock.Fournisseur":          "fas fa-truck",
        "stock.MouvementStock":       "fas fa-exchange-alt",
        "facturation":                "fas fa-file-invoice-dollar",
        "facturation.Facture":        "fas fa-receipt",
        "facturation.Client":         "fas fa-user-tie",
        "facturation.Paiement":       "fas fa-coins",
        "auth":                       "fas fa-shield-alt",
        "auth.Group":                 "fas fa-users-cog",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    "related_modal_active": True,
    "custom_css":  None,
    "custom_js":   None,
    "use_google_fonts_cdn": False,
    "show_ui_builder": False,
    "changeform_format": "collapsible",
    "changeform_format_overrides": {
        "auth.user":  "collapsible",
        "auth.group": "vertical_tabs",
    },

    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text":       False,
    "footer_small_text":       True,
    "body_small_text":         False,
    "brand_small_text":        False,
    "brand_colour":            "navbar-navy",
    "accent":                  "accent-navy",
    "navbar":                  "navbar-navy navbar-dark",
    "no_navbar_border":        True,
    "navbar_fixed":            True,
    "layout_boxed":            False,
    "footer_fixed":            False,
    "sidebar_fixed":           True,
    "sidebar":                 "sidebar-dark-navy",
    "sidebar_nav_small_text":  False,
    "sidebar_disable_expand":  False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style":  False,
    "theme":                   "default",
    "dark_mode_theme":         None,
    "button_classes": {
        "primary":   "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info":      "btn-outline-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
    "actions_sticky_top": True,
}

# ─── En-têtes sécurité (tous environnements) ─────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True   # Bloque MIME-sniffing
SECURE_BROWSER_XSS_FILTER   = True   # Filtre XSS navigateur
X_FRAME_OPTIONS              = 'DENY' # Anti-clickjacking
REFERRER_POLICY              = 'strict-origin-when-cross-origin'

# Content Security Policy — middleware personnalisé
CSP_DEFAULT_SRC  = ("'self'",)
CSP_SCRIPT_SRC   = ("'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'")
CSP_STYLE_SRC    = ("'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'")
CSP_FONT_SRC     = ("'self'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC      = ("'self'", "data:", "blob:")
CSP_CONNECT_SRC  = ("'self'",)
CSP_FRAME_SRC    = ("'none'",)

# ─── Sécurité en production uniquement ───────────────────────────────────────
if not DEBUG:
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SECURE_SSL_REDIRECT            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    # Pour les déploiements derrière un reverse proxy (nginx, Cloudflare…)
    SECURE_PROXY_SSL_HEADER        = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Validation ALLOWED_HOSTS stricte en production
    if not ALLOWED_HOSTS or all(host in {'localhost', '127.0.0.1', '0.0.0.0'} for host in ALLOWED_HOSTS):
        raise ValueError(
            "ALLOWED_HOSTS doit être défini avec le vrai domaine en production. "
            "Ex: ALLOWED_HOSTS=stockpro.mondomaine.sn dans .env"
        )
