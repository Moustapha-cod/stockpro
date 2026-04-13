from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect
from django.urls import reverse
from .models import User, ProfilUtilisateur


class ProfilInline(admin.StackedInline):
    model = ProfilUtilisateur
    can_delete = False
    verbose_name_plural = 'Profil'
    fk_name = 'utilisateur'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfilInline]
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'username')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            profil = ProfilUtilisateur.objects.get(utilisateur_id=object_id)
            return redirect(reverse('accounts:utilisateur_modifier', args=[profil.pk]))
        except ProfilUtilisateur.DoesNotExist:
            pass
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        return redirect(reverse('accounts:utilisateur_creer'))


@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'entreprise', 'role', 'actif']
    list_filter = ['role', 'actif', 'entreprise']
    search_fields = ['utilisateur__email', 'utilisateur__first_name']
