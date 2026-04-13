"""apps/stock/forms.py — Formulaires pour la gestion du stock"""

from django import forms
from .models import Produit, Categorie, Fournisseur, MouvementStock


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
            'nom', 'reference', 'code_barre', 'description',
            'categorie', 'fournisseur', 'marque', 'modele_compatible',
            'prix_achat', 'prix_vente',
            'quantite_stock', 'seuil_alerte', 'emplacement', 'unite',
            'image', 'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'code_barre': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'marque': forms.TextInput(attrs={'class': 'form-control'}),
            'modele_compatible': forms.TextInput(attrs={'class': 'form-control'}),
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
