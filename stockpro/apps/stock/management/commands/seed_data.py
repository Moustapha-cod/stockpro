"""
Commande Django : python manage.py seed_data
Génère des données de test réalistes pour StockPro SN.
"""

import random
from decimal import Decimal
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.tenants.models import Entreprise
from apps.accounts.models import User, ProfilUtilisateur
from apps.stock.models import Categorie, Fournisseur, Produit, MouvementStock
from apps.facturation.models import Client, Facture, LigneFacture, Paiement


# ── Données réalistes pièces auto au Sénégal ──────────────────────────────────

CATEGORIES = [
    ('Filtration',      '#2196F3', 'bi-funnel'),
    ('Freinage',        '#F44336', 'bi-exclamation-octagon'),
    ('Moteur',          '#FF9800', 'bi-gear'),
    ('Électricité',     '#9C27B0', 'bi-lightning'),
    ('Transmission',    '#4CAF50', 'bi-arrows-expand'),
    ('Suspension',      '#795548', 'bi-car-front'),
    ('Carrosserie',     '#607D8B', 'bi-tools'),
    ('Climatisation',   '#00BCD4', 'bi-thermometer'),
]

FOURNISSEURS = [
    ('CFAO Automotive Sénégal',   'Ibou Diallo',   '+221 33 849 00 00', 'Dakar'),
    ('Tractafric Motors',         'Moussa Koné',   '+221 33 839 20 00', 'Dakar'),
    ('Sénégal Auto Pièces',       'Fatou Ndiaye',  '+221 77 500 00 00', 'Dakar'),
    ('Al Hamdou Import',          'Abdou Sy',      '+221 70 123 45 67', 'Touba'),
    ('Pièces Express Kaolack',    'Awa Ba',         '+221 77 987 65 43', 'Kaolack'),
]

PRODUITS_TEMPLATES = [
    # (nom, ref_prefix, categorie_idx, prix_achat, prix_vente, seuil)
    ('Filtre à huile Toyota Corolla',   'FH-TOY', 0, 3500,  5500,  10),
    ('Filtre à huile Peugeot 206',      'FH-PEU', 0, 3200,  5000,  10),
    ('Filtre à air Renault Logan',      'FA-REN', 0, 4500,  7000,  8),
    ('Filtre à carburant Nissan',       'FC-NIS', 0, 5000,  8000,  5),
    ('Filtre habitacle Toyota',         'FHA-TOY',0, 4000,  6500,  5),
    ('Plaquettes de frein avant Toyota','PF-TOY', 1, 12000, 18000, 5),
    ('Plaquettes de frein Peugeot 307', 'PF-PEU', 1, 10000, 16000, 5),
    ('Disque de frein avant Renault',   'DF-REN', 1, 25000, 38000, 3),
    ('Tambour de frein arrière Toyota', 'TF-TOY', 1, 18000, 28000, 3),
    ('Liquide de frein DOT4 500ml',     'LF-DOT', 1, 3500,  6000,  15),
    ('Huile moteur 5W30 5L Total',      'HM-TOT', 2, 18000, 28000, 8),
    ('Huile moteur 10W40 5L Castrol',   'HM-CAS', 2, 16000, 25000, 8),
    ('Joint de culasse Toyota 2NZ',     'JC-TOY', 2, 22000, 35000, 3),
    ('Courroie de distribution Peugeot','CD-PEU', 2, 15000, 24000, 3),
    ('Kit distribution complet Toyota', 'KD-TOY', 2, 45000, 70000, 2),
    ('Batterie 60Ah Bosch',             'BA-BOS', 3, 55000, 80000, 3),
    ('Batterie 45Ah Yuasa',             'BA-YUA', 3, 42000, 65000, 3),
    ('Alternateur Toyota Corolla',      'AL-TOY', 3, 85000,130000, 2),
    ('Démarreur Renault Logan',         'DE-REN', 3, 65000,100000, 2),
    ('Bougie NGK Toyota',               'BG-NGK', 3, 3000,  5000,  20),
    ('Bougie Bosch Peugeot',            'BG-BOS', 3, 2800,  4500,  20),
    ('Boîte de vitesse Toyota Hilux',   'BV-TOY', 4, 280000,420000,1),
    ('Embrayage complet Peugeot 206',   'EM-PEU', 4, 75000, 115000,2),
    ('Roulement de roue avant Toyota',  'RR-TOY', 5, 18000, 28000, 5),
    ('Amortisseur avant Renault',       'AM-REN', 5, 35000, 55000, 3),
    ('Silent bloc Peugeot 307',         'SB-PEU', 5, 8000,  13000, 5),
    ('Pare-brise Toyota Corolla',       'PB-TOY', 6, 95000, 145000,1),
    ('Rétroviseur gauche Renault',      'RV-REN', 6, 22000, 35000, 2),
    ('Compresseur clim Toyota',         'CC-TOY', 7, 125000,190000,1),
    ('Gaz climatisation R134a',         'GC-134', 7, 8000,  15000, 5),
]

CLIENTS = [
    ('Garage Modou Dakar',       'entreprise', 'Modou Sarr',    '+221 77 111 22 33', 'Dakar'),
    ('Auto Service Plateau',     'entreprise', 'Cheikh Diop',   '+221 77 444 55 66', 'Dakar'),
    ('Atelier Mécanique Thiaroye','entreprise','Ibrahima Fall',  '+221 77 777 88 99', 'Thiaroye'),
    ('Transport Sow & Frères',   'entreprise', 'Mamadou Sow',   '+221 77 222 33 44', 'Dakar'),
    ('Garage Al Amine',          'entreprise', 'Amine Cissé',   '+221 70 555 66 77', 'Pikine'),
    ('Auto école Safara',        'entreprise', 'Rokhaya Ndiaye','+221 78 888 99 00', 'Saint-Louis'),
    ('Lamine Mbaye',             'particulier','',               '+221 77 100 20 30', 'Dakar'),
    ('Ousmane Traoré',           'particulier','',               '+221 76 200 30 40', 'Thiès'),
    ('Fatou Diallo',             'particulier','',               '+221 77 300 40 50', 'Dakar'),
    ('Revendeur Auto Touba',     'revendeur',  'Serigne Ba',     '+221 70 600 70 80', 'Touba'),
]


class Command(BaseCommand):
    help = 'Génère des données de test réalistes pour StockPro SN'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprimer toutes les données existantes avant de générer',
        )
        parser.add_argument(
            '--entreprise',
            type=str,
            default='AutoPièces Dakar',
            help='Nom de l\'entreprise à créer (défaut: AutoPièces Dakar)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== StockPro SN — Génération de données de test ===\n'))

        with transaction.atomic():
            if options['reset']:
                self._reset()

            entreprise = self._creer_entreprise(options['entreprise'])
            admin      = self._creer_utilisateurs(entreprise)
            categories = self._creer_categories(entreprise)
            fournisseurs = self._creer_fournisseurs(entreprise)
            produits   = self._creer_produits(entreprise, categories, fournisseurs)
            self._creer_mouvements_entree(entreprise, produits, admin)
            clients    = self._creer_clients(entreprise)
            self._creer_factures(entreprise, clients, produits, admin)

        self.stdout.write(self.style.SUCCESS('\nOK Données générées avec succès !\n'))
        self.stdout.write('  Connectez-vous avec :')
        self.stdout.write(self.style.WARNING('  Email    : admin@autopiecesdakar.sn'))
        self.stdout.write(self.style.WARNING('  Mot de passe : admin123\n'))

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _reset(self):
        self.stdout.write('  Suppression des données existantes…')
        Paiement.objects.all().delete()
        LigneFacture.objects.all().delete()
        Facture.objects.all().delete()
        Client.objects.all().delete()
        MouvementStock.objects.all().delete()
        Produit.objects.all().delete()
        Fournisseur.objects.all().delete()
        Categorie.objects.all().delete()
        ProfilUtilisateur.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Entreprise.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  OK Données supprimées'))

    # ── Entreprise ────────────────────────────────────────────────────────────

    def _creer_entreprise(self, nom):
        from django.utils.text import slugify
        slug = slugify(nom)
        entreprise, created = Entreprise.objects.get_or_create(
            slug=slug,
            defaults={
                'nom': nom,
                'adresse': 'Avenue Cheikh Anta Diop, Dakar, Sénégal',
                'telephone': '+221 33 820 00 00',
                'email': 'contact@autopiecesdakar.sn',
                'ninea': '12345678A001',
                'registre_commerce': 'SN-DKR-2020-B-12345',
                'devise': 'FCFA',
                'tva_taux': Decimal('18.00'),
                'mentions_facture': 'Tout article vendu ne sera ni repris ni échangé. Paiement comptant à la livraison.',
            }
        )
        status = 'créée' if created else 'existante'
        self.stdout.write(f'  OK Entreprise {status} : {entreprise.nom}')
        return entreprise

    # ── Utilisateurs ──────────────────────────────────────────────────────────

    def _creer_utilisateurs(self, entreprise):
        users_data = [
            ('admin@autopiecesdakar.sn',      'admin123',    'Amadou',   'Diallo',  'admin'),
            ('gestionnaire@autopiecesdakar.sn','pass1234',   'Mariama',  'Ndiaye',  'gestionnaire'),
            ('vendeur@autopiecesdakar.sn',     'pass1234',   'Oumar',    'Bâ',      'utilisateur'),
        ]

        admin = None
        for email, password, prenom, nom, role in users_data:
            # Chercher par email d'abord
            user = User.objects.filter(email=email).first()
            if not user:
                # Générer un username unique
                base_username = email.split('@')[0]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base_username}{counter}'
                    counter += 1
                user = User.objects.create(
                    email=email,
                    username=username,
                    first_name=prenom,
                    last_name=nom,
                    is_active=True,
                    is_staff=(role == 'admin'),
                )
                user.set_password(password)
                user.save()

            ProfilUtilisateur.objects.get_or_create(
                utilisateur=user,
                defaults={
                    'entreprise': entreprise,
                    'role': role,
                    'actif': True,
                }
            )

            if role == 'admin':
                admin = user

        self.stdout.write(f'  OK 3 utilisateurs créés (admin, gestionnaire, vendeur)')
        return admin

    # ── Catégories ────────────────────────────────────────────────────────────

    def _creer_categories(self, entreprise):
        cats = []
        for nom, couleur, icone in CATEGORIES:
            cat, _ = Categorie.objects.get_or_create(
                entreprise=entreprise, nom=nom,
                defaults={'couleur': couleur, 'icone': icone, 'actif': True}
            )
            cats.append(cat)
        self.stdout.write(f'  OK {len(cats)} catégories créées')
        return cats

    # ── Fournisseurs ──────────────────────────────────────────────────────────

    def _creer_fournisseurs(self, entreprise):
        fourns = []
        for nom, contact, telephone, ville in FOURNISSEURS:
            f, _ = Fournisseur.objects.get_or_create(
                entreprise=entreprise, nom=nom,
                defaults={
                    'contact': contact,
                    'telephone': telephone,
                    'pays': 'Sénégal',
                    'actif': True,
                }
            )
            fourns.append(f)
        self.stdout.write(f'  OK {len(fourns)} fournisseurs créés')
        return fourns

    # ── Produits ──────────────────────────────────────────────────────────────

    def _creer_produits(self, entreprise, categories, fournisseurs):
        produits = []
        for i, (nom, ref_prefix, cat_idx, pa, pv, seuil) in enumerate(PRODUITS_TEMPLATES):
            ref = f'{ref_prefix}-{str(i+1).zfill(3)}'
            produit, _ = Produit.objects.get_or_create(
                entreprise=entreprise, reference=ref,
                defaults={
                    'nom': nom,
                    'categorie': categories[cat_idx],
                    'fournisseur': random.choice(fournisseurs),
                    'prix_achat': Decimal(str(pa)),
                    'prix_vente': Decimal(str(pv)),
                    'seuil_alerte': seuil,
                    'quantite_stock': 0,  # sera mis à jour par les mouvements
                    'unite': 'Pièce',
                    'actif': True,
                }
            )
            produits.append(produit)
        self.stdout.write(f'  OK {len(produits)} produits créés')
        return produits

    # ── Mouvements d'entrée (stock initial) ───────────────────────────────────

    def _creer_mouvements_entree(self, entreprise, produits, user):
        nb = 0
        for produit in produits:
            if produit.quantite_stock > 0:
                continue
            qte = random.randint(5, 40)
            MouvementStock.objects.create(
                entreprise=entreprise,
                produit=produit,
                type_mouvement=MouvementStock.TypeMouvement.ENTREE,
                quantite=qte,
                prix_unitaire=produit.prix_achat,
                motif='Stock initial — données de test',
                date_mouvement=timezone.now() - timedelta(days=random.randint(30, 90)),
                cree_par=user,
            )
            nb += 1

        # Quelques produits en rupture ou alerte volontairement
        rupture_idx = random.sample(range(len(produits)), 2)
        alerte_idx  = random.sample([i for i in range(len(produits)) if i not in rupture_idx], 3)

        for idx in rupture_idx:
            p = produits[idx]
            if p.quantite_stock > 0:
                MouvementStock.objects.create(
                    entreprise=entreprise,
                    produit=p,
                    type_mouvement=MouvementStock.TypeMouvement.AJUSTEMENT,
                    quantite=0,
                    motif='Mise en rupture pour test',
                    cree_par=user,
                )

        for idx in alerte_idx:
            p = produits[idx]
            seuil = p.seuil_alerte
            if p.quantite_stock > seuil:
                MouvementStock.objects.create(
                    entreprise=entreprise,
                    produit=p,
                    type_mouvement=MouvementStock.TypeMouvement.AJUSTEMENT,
                    quantite=max(1, seuil - 1),
                    motif='Mise en alerte pour test',
                    cree_par=user,
                )

        self.stdout.write(f'  OK Mouvements de stock initiaux créés ({nb} entrées)')

    # ── Clients ───────────────────────────────────────────────────────────────

    def _creer_clients(self, entreprise):
        clients = []
        for nom, type_cl, contact, telephone, ville in CLIENTS:
            c, _ = Client.objects.get_or_create(
                entreprise=entreprise, nom=nom,
                defaults={
                    'type_client': type_cl,
                    'contact': contact,
                    'telephone': telephone,
                    'ville': ville,
                    'actif': True,
                }
            )
            clients.append(c)
        self.stdout.write(f'  OK {len(clients)} clients créés')
        return clients

    # ── Factures & paiements ──────────────────────────────────────────────────

    def _creer_factures(self, entreprise, clients, produits, user):
        today = date.today()
        nb_factures = 0
        nb_paiements = 0

        # Scénarios : payée, partielle, émise, en retard, brouillon
        scenarios = [
            # (jours_emission, jours_echeance, type_paiement)
            # payées récentes
            *[(-random.randint(1, 10),  30, 'payee')  for _ in range(5)],
            # payées anciennes
            *[(-random.randint(20, 60), 30, 'payee')  for _ in range(5)],
            # partiellement payées
            *[(-random.randint(5, 20),  30, 'tranche') for _ in range(4)],
            # dettes (crédit)
            *[(-random.randint(1, 15),  15, 'dette')   for _ in range(3)],
            # en retard
            *[(-random.randint(30, 60), -5, 'retard')  for _ in range(3)],
            # émises récentes non payées
            *[(-random.randint(1, 5),   30, 'emise')   for _ in range(3)],
        ]

        for jours_em, jours_ech, type_pmt in scenarios:
            client      = random.choice(clients)
            date_em     = today + timedelta(days=jours_em)
            date_ech    = date_em + timedelta(days=jours_ech) if jours_ech else None

            # Créer la facture
            facture = Facture(
                entreprise=entreprise,
                client=client,
                date_emission=date_em,
                date_echeance=date_ech,
                taux_tva=Decimal('18.00'),
                remise_globale=Decimal(str(random.choice([0, 0, 0, 5, 10]))),
                mode_paiement=random.choice([
                    Facture.ModePaiement.ESPECES,
                    Facture.ModePaiement.WAVE,
                    Facture.ModePaiement.ORANGE_MONEY,
                    Facture.ModePaiement.VIREMENT,
                ]),
                statut=Facture.Statut.BROUILLON,
                cree_par=user,
            )
            facture.numero = facture.generer_numero()
            facture.save()
            nb_factures += 1

            # Ajouter 2 à 5 lignes
            produits_choisis = random.sample(produits, random.randint(2, 5))
            for produit in produits_choisis:
                qte = random.randint(1, 4)
                LigneFacture.objects.create(
                    facture=facture,
                    produit=produit,
                    designation=produit.nom,
                    reference=produit.reference,
                    quantite=qte,
                    prix_unitaire_ht=produit.prix_vente,
                    remise=Decimal(str(random.choice([0, 0, 5]))),
                )

            # Calculer les totaux
            facture.recalculer_totaux()
            facture.statut = Facture.Statut.EMISE
            facture.save(update_fields=['statut'])

            montant_ttc = facture.montant_ttc

            # Appliquer les paiements selon le scénario
            if type_pmt == 'payee':
                Paiement.objects.create(
                    entreprise=entreprise,
                    facture=facture,
                    montant=montant_ttc,
                    mode_paiement=facture.mode_paiement,
                    date_paiement=date_em + timedelta(days=random.randint(0, 5)),
                    cree_par=user,
                )
                nb_paiements += 1

            elif type_pmt == 'tranche':
                # 2 tranches
                tranche1 = round(montant_ttc * Decimal('0.5'), 0)
                tranche2 = round(montant_ttc * Decimal('0.3'), 0)
                for montant, jours_plus in [(tranche1, 1), (tranche2, 10)]:
                    Paiement.objects.create(
                        entreprise=entreprise,
                        facture=facture,
                        montant=montant,
                        mode_paiement=facture.mode_paiement,
                        date_paiement=date_em + timedelta(days=jours_plus),
                        cree_par=user,
                        notes=f'Tranche {"1" if jours_plus == 1 else "2"}/2',
                    )
                    nb_paiements += 1

            elif type_pmt == 'dette':
                Paiement.objects.create(
                    entreprise=entreprise,
                    facture=facture,
                    montant=montant_ttc,
                    mode_paiement=Facture.ModePaiement.CREDIT,
                    date_paiement=date_em,
                    cree_par=user,
                    notes='Client emporte la marchandise à crédit',
                )
                nb_paiements += 1

            elif type_pmt == 'retard':
                # Aucun paiement → en retard
                pass

            elif type_pmt == 'emise':
                # Aucun paiement → émise récente
                pass

        self.stdout.write(f'  OK {nb_factures} factures créées avec {nb_paiements} paiements')
