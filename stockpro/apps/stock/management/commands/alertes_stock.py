"""
Management command : alertes_stock
Envoie un email récapitulatif des produits en rupture ou en alerte
à tous les administrateurs de chaque entreprise.

Usage :
    python manage.py alertes_stock
    python manage.py alertes_stock --entreprise 3   (une seule entreprise)
    python manage.py alertes_stock --dry-run        (affiche sans envoyer)

Cron (chaque matin à 8h) :
    0 8 * * * /var/www/stockpro/venv/bin/python /var/www/stockpro/app/manage.py alertes_stock
"""

import logging
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db.models import F
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger('securite')


class Command(BaseCommand):
    help = "Envoie les alertes stock par email aux administrateurs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--entreprise',
            type=int,
            default=None,
            help='ID entreprise spécifique (toutes par défaut)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les alertes sans envoyer les emails',
        )

    def handle(self, *args, **options):
        from apps.tenants.models import Entreprise
        from apps.stock.models import Produit
        from apps.accounts.models import ProfilUtilisateur

        entreprise_id = options['entreprise']
        dry_run = options['dry_run']

        entreprises = Entreprise.objects.filter(actif=True)
        if entreprise_id:
            entreprises = entreprises.filter(pk=entreprise_id)

        nb_emails = 0

        for entreprise in entreprises:
            # Produits en rupture (stock = 0)
            ruptures = list(Produit.objects.filter(
                entreprise=entreprise,
                actif=True,
                quantite_stock=0,
            ).select_related('categorie').order_by('nom'))

            # Produits en alerte (0 < stock <= seuil)
            alertes = list(Produit.objects.filter(
                entreprise=entreprise,
                actif=True,
                quantite_stock__gt=0,
                quantite_stock__lte=F('seuil_alerte'),
            ).select_related('categorie').order_by('quantite_stock'))

            if not ruptures and not alertes:
                self.stdout.write(f"  {entreprise.nom} - aucune alerte")
                continue

            # Destinataires : admins actifs avec email
            admins = ProfilUtilisateur.objects.filter(
                entreprise=entreprise,
                actif=True,
                role__in=['admin', 'gestionnaire'],
            ).select_related('utilisateur').exclude(utilisateur__email='')

            destinataires = [p.utilisateur.email for p in admins if p.utilisateur.email]

            if not destinataires:
                self.stdout.write(
                    self.style.WARNING(f"  {entreprise.nom} — aucun destinataire trouvé")
                )
                continue

            # Contenu email
            contexte = {
                'entreprise': entreprise,
                'ruptures': ruptures,
                'alertes': alertes,
                'nb_ruptures': len(ruptures),
                'nb_alertes': len(alertes),
            }

            sujet = (
                f"[StockPro] {len(ruptures)} rupture(s) / "
                f"{len(alertes)} alerte(s) stock - {entreprise.nom}"
            )
            corps_texte = _corps_texte(contexte)
            corps_html  = render_to_string('stock/email_alertes_stock.html', contexte)

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f"\n{'='*60}\n"
                    f"ENTREPRISE : {entreprise.nom}\n"
                    f"DESTINATAIRES : {', '.join(destinataires)}\n"
                    f"SUJET : {sujet}\n"
                    f"Ruptures : {len(ruptures)} | Alertes : {len(alertes)}\n"
                ))
                for p in ruptures:
                    self.stdout.write(f"  [RUPTURE] {p.nom} (ref. {p.reference or '-'})")
                for p in alertes:
                    self.stdout.write(
                        f"  [ALERTE]  {p.nom} stock={p.quantite_stock} / seuil={p.seuil_alerte}"
                    )
                continue

            # Envoi réel
            try:
                send_mail(
                    subject=sujet,
                    message=corps_texte,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=destinataires,
                    html_message=corps_html,
                    fail_silently=False,
                )
                nb_emails += 1
                logger.info(
                    f"ALERTE_STOCK_EMAIL entreprise={entreprise.nom} "
                    f"ruptures={len(ruptures)} alertes={len(alertes)} "
                    f"destinataires={destinataires}"
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  {entreprise.nom} — email envoyé à {', '.join(destinataires)}"
                ))
            except Exception as e:
                logger.error(f"ALERTE_STOCK_ERREUR entreprise={entreprise.nom} erreur={e}")
                self.stdout.write(self.style.ERROR(
                    f"  {entreprise.nom} — erreur d'envoi : {e}"
                ))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\n{nb_emails} email(s) envoyé(s)."))


def _corps_texte(ctx):
    """Version texte brut de l'email (fallback)."""
    lignes = [
        f"Rapport de stock — {ctx['entreprise'].nom}",
        "=" * 50,
        "",
    ]
    if ctx['ruptures']:
        lignes.append(f"RUPTURES DE STOCK ({ctx['nb_ruptures']}) :")
        for p in ctx['ruptures']:
            lignes.append(f"  - {p.nom} (réf. {p.reference or '—'})")
        lignes.append("")
    if ctx['alertes']:
        lignes.append(f"STOCKS BAS ({ctx['nb_alertes']}) :")
        for p in ctx['alertes']:
            lignes.append(
                f"  - {p.nom} : {p.quantite_stock} unité(s) "
                f"(seuil : {p.seuil_alerte})"
            )
    lignes += ["", "— StockPro SN"]
    return "\n".join(lignes)
