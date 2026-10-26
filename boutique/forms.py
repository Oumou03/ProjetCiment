from django import forms
from .models import Approvisionnement, Produit, Fournisseur, Vente, Client

class ApprovisionnementForm(forms.ModelForm):
    class Meta:
        model = Approvisionnement
        fields = ['produit', 'fournisseur', 'quantite_sacs', 'prix_achat_unitaire', 'commentaire']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'quantite_sacs': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'prix_achat_unitaire': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'commentaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optionnel'}),
        }

class VenteForm(forms.ModelForm):
    class Meta:
        model = Vente
        fields = ['produit', 'client', 'quantite_sacs', 'type_paiement', 'montant_paye', 'commentaire']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select', 'id': 'id_produit'}),
            'client': forms.Select(attrs={'class': 'form-select', 'id': 'id_client'}),
            'quantite_sacs': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'id_quantite'}),
            'type_paiement': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_paiement'}),
            'montant_paye': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'id': 'id_montant_paye'}),
            'commentaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optionnel'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cacher montant_paye par défaut
        self.fields['montant_paye'].required = False
        self.fields['montant_paye'].initial = 0

class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['nom', 'prix_achat', 'prix_vente', 'stock_actuel', 'seuil_alerte']

class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom', 'telephone', 'adresse']

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'telephone', 'adresse']