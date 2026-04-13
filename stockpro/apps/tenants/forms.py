"""apps/tenants/forms.py — Formulaire de paramètres entreprise"""

from django import forms
from .models import Entreprise


class EntrepriseForm(forms.ModelForm):
    class Meta:
        model = Entreprise
        fields = [
            'nom', 'adresse', 'telephone', 'email',
            'logo', 'ninea', 'registre_commerce',
            'devise', 'tva_taux', 'mentions_facture',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ninea': forms.TextInput(attrs={'class': 'form-control'}),
            'registre_commerce': forms.TextInput(attrs={'class': 'form-control'}),
            'devise': forms.TextInput(attrs={'class': 'form-control'}),
            'tva_taux': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mentions_facture': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Ex : Pénalité de retard de 1,5% par mois…'
            }),
        }
        labels = {
            'nom': 'Nom de l\'entreprise',
            'ninea': 'NINEA',
            'registre_commerce': 'Registre du commerce',
            'tva_taux': 'Taux TVA (%)',
            'mentions_facture': 'Mentions légales (bas de facture)',
        }
