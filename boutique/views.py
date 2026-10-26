from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib import messages
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from .models import Produit, Vente, Client, Fournisseur, Approvisionnement, Paiement
from .forms import ProduitForm, VenteForm, ApprovisionnementForm, FournisseurForm, ClientForm

# --- TABLEAU DE BORD ---
def dashboard(request):
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Sum, F
    
    # Produits
    produits = Produit.objects.all()
    alertes = Produit.objects.filter(stock_actuel__lte=F('seuil_alerte'))
    
    # Clients et finances
    clients = Client.objects.all()
    clients_avec_dette = clients.filter(solde__lt=0).count()
    clients_avec_avance = clients.filter(solde__gt=0).count()
    
    # Calcul des totaux financiers
    total_creances = abs(sum(c.solde for c in clients if c.solde < 0))
    total_avances = sum(c.solde for c in clients if c.solde > 0)
    
    # Ventes
    ventes_recentes = Vente.objects.all().order_by('-date_vente')[:10]
    ca_total = int(Vente.objects.aggregate(Sum('prix_total'))['prix_total__sum'] or 0)
    
    # Stock total (corrigé pour éviter les négatifs)
    total_sacs = 0
    for p in produits:
        if p.stock_actuel > 0:
            total_sacs += p.stock_actuel
    
    # ✅ Stock positif pour chaque produit (affichage)
    for p in produits:
        p.stock_positif = max(0, p.stock_actuel)
    
    # Produits avec stock OK (pas en alerte)
    produits_ok = produits.exclude(stock_actuel__lte=F('seuil_alerte')).count()
    
    # Ventes du mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    ventes_mois = Vente.objects.filter(date_vente__gte=debut_mois).count()
    
    # Montant total des ventes du mois
    montant_ventes_mois = Vente.objects.filter(date_vente__gte=debut_mois).aggregate(Sum('prix_total'))['prix_total__sum'] or 0
    
    # Pourcentages pour les barres de progression
    total_clients = clients.count() or 1
    pourcentage_dettes = (clients_avec_dette / total_clients) * 100
    pourcentage_avances = (clients_avec_avance / total_clients) * 100
    
    # Valeur totale du stock
    valeur_totale_stock = 0
    for p in produits:
        if p.stock_actuel > 0:
            valeur_totale_stock += p.stock_actuel * p.prix_vente
    
    context = {
        'produits': produits,
        'ventes_recentes': ventes_recentes,
        'alertes': alertes,
        'prod_form': ProduitForm(),
        'vente_form': VenteForm(),
        'appro_form': ApprovisionnementForm(),
        'fourn_form': FournisseurForm(),
        'ca_total': ca_total,
        'total_sacs': total_sacs,
        'clients_count': clients.count(),
        'clients_avec_dette': clients_avec_dette,
        'clients_avec_avance': clients_avec_avance,
        'total_creances': total_creances,
        'total_avances': total_avances,
        'ventes_mois': ventes_mois,
        'montant_ventes_mois': montant_ventes_mois,
        'produits_ok': produits_ok,
        'pourcentage_dettes': pourcentage_dettes,
        'pourcentage_avances': pourcentage_avances,
        'valeur_totale_stock': valeur_totale_stock,
    }
    return render(request, 'boutique/dashboard.html', context)

# --- GESTION DES PRODUITS ---
def liste_produits(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Produit ajouté avec succès !")
            return redirect('liste_produits')
    else:
        form = ProduitForm()
    
    produits = Produit.objects.all().order_by('-id')
    
    return render(request, 'boutique/produits.html', {
        'produits': produits,
        'produit_form': form
    })

def modifier_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == "POST":
        produit.prix_achat = int(float(request.POST.get('prix_achat', 0)))
        produit.prix_vente = int(float(request.POST.get('prix_vente', 0)))
        produit.seuil_alerte = int(float(request.POST.get('seuil_alerte', 10)))
        produit.save()
        messages.success(request, "✅ Produit mis à jour.")
    return redirect('liste_produits')

def supprimer_produit(request, pk):
    get_object_or_404(Produit, id=pk).delete()
    messages.success(request, "🗑️ Produit supprimé.")
    return redirect('liste_produits')

# --- GESTION DES STOCKS ---
def liste_stocks(request):
    produits = Produit.objects.all().order_by('stock_actuel')
    return render(request, 'boutique/stocks.html', {'produits': produits})

# --- GESTION DES VENTES ---
# --- GESTION DES VENTES ---
def liste_ventes(request):
    if request.method == 'POST':
        if 'btn_vente' in request.POST:
            # Récupération manuelle des données (sans le formulaire Django)
            try:
                produit_id = request.POST.get('produit')
                client_id = request.POST.get('client')
                quantite = int(request.POST.get('quantite_sacs'))
                type_paiement = request.POST.get('type_paiement', 'COMPTANT')
                montant_paye = int(request.POST.get('montant_paye', 0))
                commentaire = request.POST.get('commentaire', '')
                
                # Vérifications de base
                if not produit_id:
                    messages.error(request, "❌ Veuillez sélectionner un produit")
                    return redirect('liste_ventes')
                
                if quantite <= 0:
                    messages.error(request, "❌ La quantité doit être supérieure à 0")
                    return redirect('liste_ventes')
                
                # Récupérer le produit
                produit = Produit.objects.get(id=produit_id)
                
                # Vérifier le stock
                if produit.stock_actuel < quantite:
                    messages.error(request, f"❌ Stock insuffisant. Disponible: {produit.stock_actuel} sacs")
                    return redirect('liste_ventes')
                
                # Récupérer ou créer le client
                client = None
                if client_id:
                    client = Client.objects.get(id=client_id)
                else:
                    # Vérifier si c'est un nouveau client
                    nom_nouveau = request.POST.get('nouveau_client_nom')
                    if nom_nouveau:
                        client = Client.objects.create(
                            nom=nom_nouveau,
                            telephone=request.POST.get('nouveau_client_tel', ''),
                            adresse=request.POST.get('nouveau_client_adr', '')
                        )
                
                # Créer la vente
                vente = Vente(
                    produit=produit,
                    client=client,
                    quantite_sacs=quantite,
                    type_paiement=type_paiement,
                    montant_paye=montant_paye,
                    commentaire=commentaire
                )
                vente.save()
                
                # Message de succès personnalisé
                if type_paiement == 'COMPTANT':
                    msg = f"💰 Vente comptant: {quantite} sacs de {produit.nom} - {vente.prix_total} GNF"
                elif type_paiement == 'DETTE':
                    msg = f"📝 Dette enregistrée: {quantite} sacs de {produit.nom} - {vente.prix_total} GNF à payer"
                elif type_paiement == 'AVANCE':
                    msg = f"💰 Payé avec avance: {quantite} sacs de {produit.nom}"
                else:
                    msg = f"💳 Acompte: {quantite} sacs de {produit.nom} - {montant_paye} GNF payés, reste {vente.reste_a_payer} GNF"
                
                messages.success(request, f"✅ {msg}")
                
            except Produit.DoesNotExist:
                messages.error(request, "❌ Produit introuvable")
            except Client.DoesNotExist:
                messages.error(request, "❌ Client introuvable")
            except ValueError as e:
                messages.error(request, f"❌ Erreur de valeur: {str(e)}")
            except ValidationError as e:
                messages.error(request, f"❌ {str(e)}")
            except Exception as e:
                messages.error(request, f"❌ Erreur inattendue: {str(e)}")
            
            return redirect('liste_ventes')
    
    # Calcul des totaux pour l'affichage
    ventes = Vente.objects.all().order_by('-date_vente')
    
    # Calculer les créances (somme de tous les restes à payer)
    total_creances = 0
    for v in ventes:
        if v.reste_a_payer > 0:
            total_creances += v.reste_a_payer
    
    # Calculer les avances totales des clients
    total_avances = 0
    for c in Client.objects.all():
        if c.solde > 0:
            total_avances += c.solde
    
    # Compter les clients avec dette
    clients_avec_dette = Client.objects.filter(solde__lt=0).count()
    
    # Compter les ventes impayées
    ventes_impayees = Vente.objects.filter(reste_a_payer__gt=0).count()
    
    return render(request, 'boutique/ventes.html', {
        'ventes': ventes,
        'vente_form': VenteForm(),
        'produits': Produit.objects.all(),
        'clients': Client.objects.all(),
        'total_creances': total_creances,
        'total_avances': total_avances,
        'clients_avec_dette': clients_avec_dette,
        'ventes_impayees': ventes_impayees,
    })
def modifier_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    ancienne_quantite = vente.quantite_sacs
    
    if request.method == 'POST':
        form = VenteForm(request.POST, instance=vente)
        if form.is_valid():
            nouvelle_vente = form.save(commit=False)
            produit = nouvelle_vente.produit
            stock_disponible = produit.stock_actuel + ancienne_quantite
            
            if stock_disponible >= nouvelle_vente.quantite_sacs:
                produit.stock_actuel = stock_disponible - nouvelle_vente.quantite_sacs
                produit.save()
                nouvelle_vente.save()
                messages.success(request, "✅ Vente modifiée.")
                return redirect('liste_ventes')
            else:
                messages.error(request, f"❌ Stock insuffisant. Disponible: {stock_disponible} sacs")
    else:
        form = VenteForm(instance=vente)
    
    return render(request, 'boutique/modifier_vente.html', {'form': form, 'vente': vente})

def supprimer_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if request.method == 'POST':
        produit = vente.produit
        produit.stock_actuel += vente.quantite_sacs
        produit.save()
        if vente.client:
            vente.client.solde += vente.prix_total
            vente.client.save()
        vente.delete()
        messages.success(request, f"↩️ Vente supprimée.")
    return redirect('liste_ventes')

# --- GESTION DES CLIENTS --- ✅ FONCTION MANQUANTE AJOUTÉE
def liste_clients(request):
    if request.method == 'POST':
        # Vérifier si c'est un ajout ou une modification
        client_id = request.POST.get('client_id')
        nom = request.POST.get('nom')
        telephone = request.POST.get('telephone', '')
        adresse = request.POST.get('adresse', '')
        
        if client_id:  # MODIFICATION
            client = get_object_or_404(Client, id=client_id)
            client.nom = nom
            client.telephone = telephone
            client.adresse = adresse
            client.save()
            messages.success(request, f"✅ Client '{nom}' modifié avec succès !")
        else:  # AJOUT
            Client.objects.create(
                nom=nom,
                telephone=telephone,
                adresse=adresse
            )
            messages.success(request, f"✅ Client '{nom}' ajouté avec succès !")
        
        return redirect('liste_clients')
    
    clients = Client.objects.all().order_by('-date_creation')
    return render(request, 'boutique/clients.html', {'clients': clients})

def details_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    commandes = Vente.objects.filter(client=client).order_by('-date_vente')
    paiements = Paiement.objects.filter(client=client).order_by('-date_paiement')
    total_achats = int(sum(v.prix_total for v in commandes))
    total_verses = int(sum(p.montant for p in paiements))
    
    context = {
        'client': client,
        'commandes': commandes,
        'paiements': paiements,
        'reste_a_payer': total_achats - total_verses,
        'total_achats': total_achats,
        'total_verses': total_verses,
    }
    return render(request, 'boutique/details_client.html', context)

def creer_paiement(request, client_id):
    if request.method == "POST":
        client = get_object_or_404(Client, id=client_id)
        
        try:
            montant = int(float(request.POST.get('montant', 0)))
        except:
            montant = 0
        
        if montant > 0:
            commentaire = request.POST.get('commentaire', '')
            
            # Avant le paiement
            ventes_dette_avant = Vente.objects.filter(
                client=client, 
                type_paiement='DETTE',
                reste_a_payer__gt=0
            ).count()
            
            montant_total_dettes = sum(v.reste_a_payer for v in Vente.objects.filter(
                client=client, 
                type_paiement='DETTE',
                reste_a_payer__gt=0
            ))
            
            # Création du paiement
            paiement = Paiement.objects.create(
                client=client,
                montant=montant,
                commentaire=commentaire
            )
            
            # Après le paiement
            client.refresh_from_db()
            ventes_dette_apres = Vente.objects.filter(
                client=client, 
                type_paiement='DETTE',
                reste_a_payer__gt=0
            ).count()
            
            # Message personnalisé
            if ventes_dette_avant > 0:
                if ventes_dette_apres == 0:
                    messages.success(
                        request, 
                        f"✅ TOUTES LES DETTES REMBOURSÉES !\n"
                        f"💰 Montant versé: {montant} GNF\n"
                        f"📊 {ventes_dette_avant} dette(s) soldée(s)\n"
                        f"💵 Solde actuel: {client.solde} GNF"
                    )
                elif montant >= montant_total_dettes:
                    messages.success(
                        request, 
                        f"✅ Dettes totalement remboursées !\n"
                        f"💰 Montant versé: {montant} GNF\n"
                        f"✨ Plus aucune dette en cours"
                    )
                else:
                    messages.success(
                        request, 
                        f"✅ Remboursement partiel\n"
                        f"💰 Montant versé: {montant} GNF\n"
                        f"📊 Dettes restantes: {ventes_dette_apres}\n"
                        f"💵 Reste à payer: {client.solde_positif if client.solde < 0 else 0} GNF"
                    )
            else:
                messages.success(
                    request, 
                    f"💰 Nouvelle avance enregistrée\n"
                    f"💵 Avance: {client.solde} GNF"
                )
        else:
            messages.error(request, "❌ Le montant doit être supérieur à 0")
    
    return redirect('details_client', client_id=client_id)

def supprimer_client(request, pk):
    client = get_object_or_404(Client, id=pk)
    nom_client = client.nom
    
    if request.method == 'POST':
        # Supprimer d'abord les paiements et ventes liés
        Paiement.objects.filter(client=client).delete()
        Vente.objects.filter(client=client).delete()
        # Puis supprimer le client
        client.delete()
        messages.success(request, f"🗑️ Client '{nom_client}' et toutes ses données supprimés.")
    
    return redirect('liste_clients')

# --- GESTION FOURNISSEURS ---
def liste_fournisseurs(request):
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Fournisseur enregistré.")
            return redirect('liste_fournisseurs')
    
    fournisseurs = Fournisseur.objects.all()
    
    # Statistiques par fournisseur
    stats = []
    for f in fournisseurs:
        total_sacs = Approvisionnement.objects.filter(fournisseur=f).aggregate(Sum('quantite_sacs'))['quantite_sacs__sum'] or 0
        nb_produits = Approvisionnement.objects.filter(fournisseur=f).values('produit').distinct().count()
        stats.append({
            'fournisseur': f,
            'total_sacs': total_sacs,
            'nb_produits': nb_produits
        })
    
    return render(request, 'boutique/fournisseurs.html', {
        'fournisseurs': fournisseurs,
        'stats': stats,
        'fourn_form': FournisseurForm()
    })

def details_fournisseur(request, fournisseur_id):
    fournisseur = get_object_or_404(Fournisseur, id=fournisseur_id)
    approvisionnements = Approvisionnement.objects.filter(fournisseur=fournisseur).order_by('-date_entree')
    
    total_sacs = approvisionnements.aggregate(Sum('quantite_sacs'))['quantite_sacs__sum'] or 0
    montant_total = sum(a.quantite_sacs * a.prix_achat_unitaire for a in approvisionnements)
    produits_distincts = approvisionnements.values('produit').distinct().count()
    derniere_livraison = approvisionnements.first()
    
    return render(request, 'boutique/details_fournisseur.html', {
        'fournisseur': fournisseur,
        'approvisionnements': approvisionnements,
        'total_sacs': total_sacs,
        'montant_total': montant_total,
        'produits_distincts': produits_distincts,
        'derniere_livraison': derniere_livraison,
    })

def supprimer_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, id=pk)
    if request.method == 'POST':
        fournisseur.delete()
        messages.success(request, "🗑️ Fournisseur supprimé.")
    return redirect('liste_fournisseurs')

# --- GESTION APPROVISIONNEMENTS ---
def liste_approvisionnements(request):
    if request.method == 'POST':
        form = ApprovisionnementForm(request.POST)
        if form.is_valid():
            appro = form.save(commit=False)
            
            # Récupérer le produit et son stock
            produit = Produit.objects.get(pk=appro.produit.pk)
            stock_avant = produit.stock_actuel
            
            # AUGMENTER LE STOCK (UNE SEULE FOIS)
            produit.stock_actuel += appro.quantite_sacs
            produit.save()
            
            # Sauvegarder l'approvisionnement
            appro.save()
            
            messages.success(
                request, 
                f"✅ ARRIVAGE RÉUSSI !\n"
                f"Produit: {produit.nom}\n"
                f"Fournisseur: {appro.fournisseur.nom}\n"
                f"Quantité: {appro.quantite_sacs} sacs\n"
                f"Stock: {stock_avant} → {produit.stock_actuel} sacs"
            )
            return redirect('liste_approvisionnements')
    
    # Statistiques par fournisseur pour l'affichage
    stats_fournisseurs = []
    for fournisseur in Fournisseur.objects.all():
        total_sacs = Approvisionnement.objects.filter(fournisseur=fournisseur).aggregate(Sum('quantite_sacs'))['quantite_sacs__sum'] or 0
        nb_produits = Approvisionnement.objects.filter(fournisseur=fournisseur).values('produit').distinct().count()
        stats_fournisseurs.append({
            'fournisseur': fournisseur,
            'total_sacs': total_sacs,
            'nb_produits': nb_produits
        })
    
    return render(request, 'boutique/approvisionnements.html', {
        'approvisionnements': Approvisionnement.objects.all().order_by('-date_entree'),
        'form': ApprovisionnementForm(),
        'stats_fournisseurs': stats_fournisseurs,
    })

def modifier_approvisionnement(request, pk):
    appro = get_object_or_404(Approvisionnement, pk=pk)
    ancienne_quantite = appro.quantite_sacs
    ancien_produit = appro.produit

    if request.method == 'POST':
        form = ApprovisionnementForm(request.POST, instance=appro)
        if form.is_valid():
            nouvel_appro = form.save(commit=False)
            
            # Cas 1: Même produit
            if ancien_produit.pk == nouvel_appro.produit.pk:
                difference = nouvel_appro.quantite_sacs - ancienne_quantite
                ancien_produit.stock_actuel += difference
                ancien_produit.save()
            
            # Cas 2: Produit changé
            else:
                # Remettre l'ancien produit
                ancien_produit.stock_actuel -= ancienne_quantite
                ancien_produit.save()
                
                # Ajouter au nouveau produit
                nouveau_produit = nouvel_appro.produit
                nouveau_produit.stock_actuel += nouvel_appro.quantite_sacs
                nouveau_produit.save()
            
            nouvel_appro.save()
            messages.success(request, "✅ Approvisionnement modifié.")
            return redirect('liste_approvisionnements')
    else:
        form = ApprovisionnementForm(instance=appro)
    
    return render(request, 'boutique/modifier_appro.html', {'form': form, 'appro': appro})

def supprimer_approvisionnement(request, pk):
    appro = get_object_or_404(Approvisionnement, pk=pk)
    produit = appro.produit
    
    if produit.stock_actuel >= appro.quantite_sacs:
        produit.stock_actuel -= appro.quantite_sacs
        produit.save()
        appro.delete()
        messages.success(request, f"🗑️ Arrivage supprimé. Stock: {produit.stock_actuel} sacs")
    else:
        messages.error(request, f"❌ Impossible: stock ({produit.stock_actuel}) < quantité à retirer ({appro.quantite_sacs})")
    
    return redirect('liste_approvisionnements')