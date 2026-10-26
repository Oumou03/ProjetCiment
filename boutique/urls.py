from django.urls import path
from . import views

urlpatterns = [
    
    # DASHBOARD
    path('', views.dashboard, name='dashboard'),
    
    # STOCKS
    path('stocks/', views.liste_stocks, name='liste_stocks'),
    
    # PRODUITS
    path('produits/', views.liste_produits, name='liste_produits'),
    path('produits/modifier/<int:pk>/', views.modifier_produit, name='modifier_produit'),
    path('produits/supprimer/<int:pk>/', views.supprimer_produit, name='supprimer_produit'),
    
    # VENTES
    path('ventes/', views.liste_ventes, name='liste_ventes'),
    path('ventes/modifier/<int:pk>/', views.modifier_vente, name='modifier_vente'),
    path('ventes/supprimer/<int:pk>/', views.supprimer_vente, name='supprimer_vente'),
    
    # CLIENTS
    path('clients/', views.liste_clients, name='liste_clients'),
    path('clients/<int:client_id>/', views.details_client, name='details_client'),
    path('clients/<int:client_id>/paiement/', views.creer_paiement, name='creer_paiement'),
    path('clients/supprimer/<int:pk>/', views.supprimer_client, name='supprimer_client'),
    
    # FOURNISSEURS
    path('fournisseurs/', views.liste_fournisseurs, name='liste_fournisseurs'),
    path('fournisseurs/supprimer/<int:pk>/', views.supprimer_fournisseur, name='supprimer_fournisseur'),
    path('fournisseurs/<int:fournisseur_id>/', views.details_fournisseur, name='details_fournisseur'),  # ✅ Changé ici
    
    # APPROVISIONNEMENTS
    path('approvisionnements/', views.liste_approvisionnements, name='liste_approvisionnements'),
    path('approvisionnements/modifier/<int:pk>/', views.modifier_approvisionnement, name='modifier_approvisionnement'),
    path('approvisionnements/supprimer/<int:pk>/', views.supprimer_approvisionnement, name='supprimer_approvisionnement'),
]