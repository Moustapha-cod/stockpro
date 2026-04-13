# gunicorn.conf.py — Configuration Gunicorn pour StockPro SN
import multiprocessing

# Adresse et port d'écoute
bind = "0.0.0.0:8000"

# Nombre de workers = 2 x CPU + 1 (recommandé)
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker (sync par défaut, gvisor pour async si besoin)
worker_class = "sync"

# Timeout worker (augmenter si exports lents)
timeout = 120

# Redémarrage automatique après N requêtes (évite les fuites mémoire)
max_requests = 1000
max_requests_jitter = 100

# Journalisation
accesslog = "-"       # stdout
errorlog  = "-"       # stderr
loglevel  = "warning" # info en debug, warning en production

# Sécurité
limit_request_line   = 4094   # Taille max URI
limit_request_fields = 100    # Nb max d'en-têtes HTTP
limit_request_field_size = 8190

# Graceful restart
graceful_timeout = 30
keepalive = 5
