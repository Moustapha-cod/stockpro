"""
apps/common/validators.py
Validateurs et utilitaires pour les uploads de fichiers.
"""

import os
import uuid
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class CheminUploadSecurise:
    """Callable sérialisable par Django pour générer des chemins d'upload sûrs."""

    def __init__(self, sous_dossier):
        self.sous_dossier = sous_dossier

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        nom_securise = f"{uuid.uuid4().hex}{ext}"
        return os.path.join(self.sous_dossier, nom_securise)


def chemin_upload_securise(sous_dossier):
    """
    Retourne une fonction upload_to qui génère un nom de fichier aléatoire.
    Ex: chemin_upload_securise('produits') → 'produits/a3f2c1d4e5b6.jpg'
    """
    return CheminUploadSecurise(sous_dossier)


# Types MIME autorisés pour les images
MIME_TYPES_IMAGES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
}

# Taille max : 5 Mo
TAILLE_MAX_IMAGE = 5 * 1024 * 1024  # 5 Mo en octets


def valider_image(fichier):
    """Valide le type MIME et la taille d'un fichier image."""

    # Vérification de la taille
    if fichier.size > TAILLE_MAX_IMAGE:
        raise ValidationError(
            f"La taille du fichier ({fichier.size // (1024*1024)} Mo) "
            f"dépasse la limite autorisée de 5 Mo."
        )

    # Vérification de l'extension
    ext = os.path.splitext(fichier.name)[1].lower()
    extensions_autorisees = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    if ext not in extensions_autorisees:
        raise ValidationError(
            f"Extension « {ext} » non autorisée. "
            f"Formats acceptés : JPG, PNG, WEBP, GIF."
        )

    # Vérification du contenu réel du fichier (magic bytes)
    entete = fichier.read(16)
    fichier.seek(0)  # Remettre le curseur au début

    # Signatures magic bytes des formats image
    signatures = {
        b'\xff\xd8\xff':             'image/jpeg',
        b'\x89PNG\r\n\x1a\n':       'image/png',
        b'RIFF':                     'image/webp',  # complété ci-dessous
        b'GIF87a':                   'image/gif',
        b'GIF89a':                   'image/gif',
    }

    mime_detecte = None
    for signature, mime in signatures.items():
        if entete.startswith(signature):
            # Cas WEBP : vaut RIFF....WEBP
            if signature == b'RIFF' and b'WEBP' not in entete:
                continue
            mime_detecte = mime
            break

    if mime_detecte is None:
        raise ValidationError(
            "Le fichier ne semble pas être une image valide. "
            "Formats acceptés : JPG, PNG, WEBP, GIF."
        )
