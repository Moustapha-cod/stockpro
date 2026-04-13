from django.contrib import admin
from django.utils.html import format_html
from .models import Entreprise


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display  = ['logo_vignette', 'nom', 'telephone', 'email', 'devise', 'statut_badge', 'date_creation']
    list_display_links = ['nom']
    search_fields = ['nom', 'email', 'telephone', 'ninea']
    list_filter   = ['actif', 'devise']
    readonly_fields = ['date_creation', 'date_modification', 'logo_vignette']
    ordering      = ['-actif', 'nom']

    fieldsets = (
        ('Identité', {
            'fields': ('nom', 'slug', 'logo', 'logo_vignette')
        }),
        ('Coordonnées', {
            'fields': ('adresse', 'telephone', 'email')
        }),
        ('Informations légales', {
            'fields': ('ninea', 'registre_commerce', 'mentions_facture')
        }),
        ('Paramètres', {
            'fields': ('devise', 'tva_taux', 'actif')
        }),
        ('Horodatage', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',),
        }),
    )

    def logo_vignette(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:36px;width:36px;object-fit:contain;border-radius:4px;border:1px solid #dee2e6;">',
                obj.logo.url
            )
        return format_html('<span style="color:#aaa;">—</span>')
    logo_vignette.short_description = 'Logo'

    def statut_badge(self, obj):
        if obj.actif:
            return format_html('<span style="background:#d1e7dd;color:#0a3622;padding:2px 10px;border-radius:20px;font-size:.78rem;font-weight:600;">Actif</span>')
        return format_html('<span style="background:#e2e3e5;color:#41464b;padding:2px 10px;border-radius:20px;font-size:.78rem;font-weight:600;">Inactif</span>')
    statut_badge.short_description = 'Statut'
