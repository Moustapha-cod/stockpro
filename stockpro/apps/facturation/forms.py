"""apps/facturation/forms.py — Formulaires Clients, Factures, Paiements"""

from django import forms
from .models import Client, Facture, LigneFacture, Paiement
from apps.stock.models import Produit


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'type_client', 'contact', 'telephone', 'telephone2',
                  'email', 'adresse', 'ville', 'ninea', 'notes', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'type_client': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone2': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ville': forms.TextInput(attrs={'class': 'form-control'}),
            'ninea': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = ['client', 'date_emission', 'date_echeance', 'taux_tva',
                  'remise_globale', 'mode_paiement', 'objet', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'date_emission': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_echeance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'taux_tva': forms.NumberInput(attrs={'class': 'form-control'}),
            'remise_globale': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'objet': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entreprise = entreprise
        if entreprise:
            self.fields['client'].queryset = Client.objects.filter(
                entreprise=entreprise, actif=True
            ).order_by('nom')

    def clean_client(self):
        client = self.cleaned_data.get('client')
        if client and self.entreprise and client.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Client invalide.")
        return client


class LigneFactureForm(forms.ModelForm):
    class Meta:
        model = LigneFacture
        fields = ['produit', 'designation', 'quantite', 'prix_unitaire_ht', 'remise']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select form-select-sm ligne-produit'}),
            'designation': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control form-control-sm ligne-qte', 'min': 1}),
            'prix_unitaire_ht': forms.NumberInput(attrs={'class': 'form-control form-control-sm ligne-prix'}),
            'remise': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entreprise = entreprise
        if entreprise:
            self.fields['produit'].queryset = Produit.objects.filter(
                entreprise=entreprise, actif=True
            ).order_by('nom')
        self.fields['produit'].required = False

    def clean_produit(self):
        produit = self.cleaned_data.get('produit')
        if produit and self.entreprise and produit.entreprise_id != self.entreprise.pk:
            raise forms.ValidationError("Produit invalide.")
        return produit


LigneFactureFormSet = forms.inlineformset_factory(
    Facture,
    LigneFacture,
    form=LigneFactureForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['montant', 'mode_paiement', 'date_paiement', 'reference_paiement', 'notes']
        widgets = {
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'date_paiement': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_paiement': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, facture=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.facture = facture

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant is not None and self.facture:
            if montant <= 0:
                raise forms.ValidationError("Le montant doit être supérieur à 0.")
            if montant > self.facture.montant_restant:
                raise forms.ValidationError(
                    f"Le montant ({montant:,.0f} FCFA) dépasse le solde restant "
                    f"({self.facture.montant_restant:,.0f} FCFA)."
                )
        return montant
