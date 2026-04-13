from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from .models import User, ProfilUtilisateur


class UtilisateurCreateForm(UserCreationForm):
    """Formulaire de création d'un utilisateur avec son profil."""

    first_name = forms.CharField(label='Prénom', max_length=150)
    last_name  = forms.CharField(label='Nom', max_length=150)
    telephone  = forms.CharField(label='Téléphone', max_length=20, required=False)
    role       = forms.ChoiceField(label='Rôle', choices=ProfilUtilisateur.Role.choices)
    entreprise = forms.ModelChoiceField(
        label='Entreprise',
        queryset=None,
        required=False,
        empty_label='— Aucune —',
    )

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, requesting_user=None, current_entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tenants.models import Entreprise
        self.requesting_user    = requesting_user
        self.current_entreprise = current_entreprise

        if requesting_user and requesting_user.is_superuser:
            self.fields['entreprise'].queryset = Entreprise.objects.filter(actif=True).order_by('nom')
        else:
            # L'admin d'entreprise crée dans sa propre entreprise — champ masqué
            self.fields['entreprise'].queryset = Entreprise.objects.none()
            self.fields['entreprise'].required = False
            self.fields['entreprise'].widget   = forms.HiddenInput()

        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault('class', 'form-control')
        self.fields['role'].widget.attrs['class'] = 'form-select'
        if 'entreprise' in self.fields and not isinstance(self.fields['entreprise'].widget, forms.HiddenInput):
            self.fields['entreprise'].widget.attrs['class'] = 'form-select'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        # username = email par défaut (tronqué à 150)
        user.username   = self.cleaned_data['email'][:150]
        if commit:
            user.save()
            entreprise = self.cleaned_data.get('entreprise') or self.current_entreprise
            ProfilUtilisateur.objects.create(
                utilisateur=user,
                entreprise=entreprise,
                role=self.cleaned_data['role'],
                telephone=self.cleaned_data.get('telephone', ''),
            )
        return user


class UtilisateurEditForm(forms.ModelForm):
    """Formulaire de modification d'un utilisateur existant."""

    telephone  = forms.CharField(label='Téléphone', max_length=20, required=False)
    role       = forms.ChoiceField(label='Rôle', choices=ProfilUtilisateur.Role.choices)
    actif      = forms.BooleanField(label='Compte actif', required=False)
    entreprise = forms.ModelChoiceField(
        label='Entreprise',
        queryset=None,
        required=False,
        empty_label='— Aucune —',
    )

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, requesting_user=None, profil=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tenants.models import Entreprise
        self.requesting_user = requesting_user
        self.profil_instance = profil

        if profil:
            self.fields['telephone'].initial  = profil.telephone
            self.fields['role'].initial       = profil.role
            self.fields['actif'].initial      = profil.actif
            self.fields['entreprise'].initial = profil.entreprise_id

        if requesting_user and requesting_user.is_superuser:
            self.fields['entreprise'].queryset = Entreprise.objects.filter(actif=True).order_by('nom')
        else:
            self.fields['entreprise'].queryset  = Entreprise.objects.none()
            self.fields['entreprise'].required  = False
            self.fields['entreprise'].widget    = forms.HiddenInput()

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault('class', 'form-control')
        self.fields['role'].widget.attrs['class'] = 'form-select'
        if 'entreprise' in self.fields and not isinstance(self.fields['entreprise'].widget, forms.HiddenInput):
            self.fields['entreprise'].widget.attrs['class'] = 'form-select'

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.profil_instance:
            self.profil_instance.telephone = self.cleaned_data.get('telephone', '')
            self.profil_instance.role      = self.cleaned_data['role']
            self.profil_instance.actif     = self.cleaned_data.get('actif', True)
            if self.requesting_user and self.requesting_user.is_superuser:
                self.profil_instance.entreprise = self.cleaned_data.get('entreprise')
            self.profil_instance.save()
        return user


class PasswordChangeForm(SetPasswordForm):
    """Formulaire de réinitialisation de mot de passe."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MonProfilForm(forms.ModelForm):
    """Formulaire de modification du profil de l'utilisateur connecté."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Prénom',
            'last_name':  'Nom',
            'email':      'Adresse email',
        }
