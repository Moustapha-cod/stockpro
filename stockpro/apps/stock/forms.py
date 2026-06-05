"""apps/stock/forms.py — Formulaires pour la gestion du stock"""

from django import forms
from django.forms import inlineformset_factory
from .models import Produit, Categorie, Fournisseur, MouvementStock, CompatibiliteVehicule


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description', 'couleur', 'icone', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'couleur': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-tag'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom', 'contact', 'telephone', 'email', 'adresse', 'pays', 'notes', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'reference', 'description',
            'categorie', 'fournisseur', 'marque', 'type_vehicule',
            'reference_oem', 'reference_equivalente',
            'prix_achat', 'prix_vente',
            'quantite_stock', 'seuil_alerte', 'emplacement', 'unite',
            'image', 'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'marque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bosch, Brembo, Valeo…'}),
            'type_vehicule': forms.Select(attrs={'class': 'form-select'}),
            'reference_oem': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A0004200983, 3C0 615 301 D'}),
            'reference_equivalente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ATE 24.0120, LPR BK1030, TRW DF4778'}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control'}),
            'prix_vente': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantite_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control'}),
            'emplacement': forms.TextInput(attrs={'class': 'form-control'}),
            'unite': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entreprise = entreprise
        if entreprise:
            self.fields['categorie'].queryset = Categorie.objects.filter(
                entreprise=entreprise, actif=True
            )
            self.fields['fournisseur'].queryset = Fournisseur.objects.filter(
                entreprise=entreprise, actif=True
            )

    def clean_categorie(self):
        cat = self.cleaned_data.get('categorie')
        if cat and self.entreprise and cat.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Catégorie invalide.")
        return cat

    def clean_fournisseur(self):
        f = self.cleaned_data.get('fournisseur')
        if f and self.entreprise and f.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Fournisseur invalide.")
        return f


class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = ['produit', 'type_mouvement', 'quantite', 'prix_unitaire',
                  'fournisseur', 'reference_document', 'motif']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'type_mouvement': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'prix_unitaire': forms.NumberInput(attrs={'class': 'form-control'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'reference_document': forms.TextInput(attrs={'class': 'form-control'}),
            'motif': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entreprise = entreprise
        if entreprise:
            self.fields['produit'].queryset = Produit.objects.filter(
                entreprise=entreprise, actif=True
            ).order_by('nom')
            self.fields['fournisseur'].queryset = Fournisseur.objects.filter(
                entreprise=entreprise, actif=True
            )

    def clean_produit(self):
        produit = self.cleaned_data.get('produit')
        if produit and self.entreprise and produit.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Produit invalide.")
        return produit

    def clean_fournisseur(self):
        f = self.cleaned_data.get('fournisseur')
        if f and self.entreprise and f.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Fournisseur invalide.")
        return f


class CompatibiliteVehiculeForm(forms.ModelForm):

    ANNEE_MIN = 1900
    ANNEE_MAX_OFFSET = 5  # années dans le futur autorisées

    class Meta:
        model = CompatibiliteVehicule
        fields = ['marque', 'modele', 'annee_debut', 'annee_fin', 'carburant']
        widgets = {
            'marque': forms.TextInput(attrs={
                'class': 'form-control compat-marque',
                'placeholder': 'Ex: Renault Trucks, Mercedes…',
                'autocomplete': 'off',
            }),
            'modele': forms.TextInput(attrs={
                'class': 'form-control compat-modele',
                'placeholder': 'Ex: T, Actros, Partner…',
                'autocomplete': 'off',
            }),
            'annee_debut': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2015',
                'min': 1900,
                'max': 2050,
            }),
            'annee_fin': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2024',
                'min': 1900,
                'max': 2050,
            }),
            'carburant': forms.Select(attrs={'class': 'form-select'}),
        }

    def _valider_annee(self, annee, nom_champ):
        import datetime
        annee_max = datetime.date.today().year + self.ANNEE_MAX_OFFSET
        if annee is not None and not (self.ANNEE_MIN <= annee <= annee_max):
            raise forms.ValidationError(
                f"L'année doit être comprise entre {self.ANNEE_MIN} et {annee_max}."
            )
        return annee

    def clean_annee_debut(self):
        return self._valider_annee(self.cleaned_data.get('annee_debut'), 'annee_debut')

    def clean_annee_fin(self):
        return self._valider_annee(self.cleaned_data.get('annee_fin'), 'annee_fin')

    def clean(self):
        cleaned = super().clean()
        debut = cleaned.get('annee_debut')
        fin = cleaned.get('annee_fin')
        if debut and fin and fin < debut:
            self.add_error('annee_fin', "L'année de fin ne peut pas être antérieure à l'année de début.")
        return cleaned


CompatibiliteFormSet = inlineformset_factory(
    Produit,
    CompatibiliteVehicule,
    form=CompatibiliteVehiculeForm,
    extra=0,
    can_delete=True,
    min_num=0,
)
