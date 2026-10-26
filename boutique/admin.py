from django.contrib import admin
from .models import Produit, Vente, Client, Fournisseur, Approvisionnement, Paiement

@admin.register(Approvisionnement)
class ApprovisionnementAdmin(admin.ModelAdmin):
    list_display = ('produit', 'fournisseur', 'quantite_sacs', 'date_entree')

@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('produit', 'client', 'quantite_sacs', 'prix_total', 'date_vente')
@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prix_achat', 'prix_vente', 'stock_actuel', 'seuil_alerte')

admin.site.register(Client)
admin.site.register(Fournisseur)
admin.site.register(Paiement)