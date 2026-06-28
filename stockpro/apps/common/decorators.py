"""apps/common/decorators.py — Décorateurs transversaux."""

from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse


def rate_limit(max_calls=60, period=60):
    """
    Limite les appels API par utilisateur authentifié.

    max_calls : nombre max de requêtes dans la fenêtre
    period    : durée de la fenêtre en secondes

    Avec 3 workers gunicorn et LocMemCache (par process), la limite
    effective est max_calls × nb_workers — acceptable sans Redis.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            key = f'rl:{request.user.pk}:{func.__name__}'
            try:
                # cache.add() est atomique : pose la clé seulement si absente
                if not cache.add(key, 1, period):
                    count = cache.incr(key)
                    if count > max_calls:
                        return JsonResponse(
                            {'error': 'Trop de requêtes. Veuillez patienter.'},
                            status=429,
                            headers={'Retry-After': str(period)},
                        )
            except Exception:
                # Si le cache est indisponible, on laisse passer plutôt que bloquer
                pass
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
