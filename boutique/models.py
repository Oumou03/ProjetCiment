from django.db import models
from django.core.exceptions import ValidationError

class Fournisseur(models.Model):
    nom = models.CharField(max_length=150)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True, null=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom
    
    class Meta:
        ordering = ['nom']

class Produit(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Marque/Type")
    prix_achat = models.BigIntegerField(default=0)
    prix_vente = models.BigIntegerField(default=0)
    stock_actuel = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=10)
    fournisseurs = models.ManyToManyField(Fournisseur, through='Approvisionnement', related_name='produits')

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if self.stock_actuel < 0:
            self.stock_actuel = 0
        super().save(*args, **kwargs)

    @property
    def stock_securise(self):
        return max(0, self.stock_actuel)
    
    @property
    def alerte_stock(self):
        return self.stock_actuel <= self.seuil_alerte
    
    @property
    def liste_fournisseurs(self):
        return ", ".join([f.nom for f in self.fournisseurs.distinct()])

class Client(models.Model):
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True)
    solde = models.BigIntegerField(default=0) 
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    @property
    def solde_positif(self):
        return abs(self.solde)

class Approvisionnement(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
    quantite_sacs = models.IntegerField(default=0)
    prix_achat_unitaire = models.BigIntegerField(default=0)
    date_entree = models.DateTimeField(auto_now_add=True)
    commentaire = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.produit.nom} - {self.fournisseur.nom} - {self.quantite_sacs} sacs"
    
    class Meta:
        ordering = ['-date_entree']

class Vente(models.Model):
    TYPE_PAIEMENT = [
        ('COMPTANT', 'Paiement Comptant'),
        ('DETTE', 'Dette Totale'),
        ('ACOMPTE', 'Acompte'),
        ('AVANCE', 'Payé par avance'),
    ]
    
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    quantite_sacs = models.PositiveIntegerField()
    prix_total = models.BigIntegerField(default=0)
    montant_paye = models.BigIntegerField(default=0)
    type_paiement = models.CharField(max_length=20, choices=TYPE_PAIEMENT, default='COMPTANT')
    reste_a_payer = models.BigIntegerField(default=0)
    date_vente = models.DateTimeField(auto_now_add=True)
    commentaire = models.CharField(max_length=255, blank=True, default='')

    def save(self, *args, **kwargs):
        if not self.pk:
            # Vérification du stock
            if self.produit.stock_actuel < self.quantite_sacs:
                raise ValidationError(f"Stock insuffisant. Disponible: {self.produit.stock_actuel} sacs")
            
            # Calcul du prix total
            self.prix_total = self.quantite_sacs * self.produit.prix_vente
            
            # LOGIQUE INTELLIGENTE : Utiliser l'avance si disponible
            if self.client and self.client.solde > 0:
                avance = self.client.solde
                
                if avance >= self.prix_total:
                    # L'avance couvre tout
                    self.montant_paye = self.prix_total
                    self.reste_a_payer = 0
                    self.type_paiement = 'AVANCE'
                    self.client.solde -= self.prix_total
                    self.commentaire = f"Payé avec avance de {avance} GNF"
                    
                else:
                    # L'avance ne couvre qu'une partie
                    self.montant_paye = avance
                    self.reste_a_payer = self.prix_total - avance
                    self.type_paiement = 'ACOMPTE'
                    self.client.solde = 0
                    self.commentaire = f"Avance utilisée: {avance} GNF, reste dû: {self.reste_a_payer} GNF"
                    
                self.client.save()
                
            else:
                # Logique normale selon le type de paiement choisi
                if self.type_paiement == 'COMPTANT':
                    self.montant_paye = self.prix_total
                    self.reste_a_payer = 0
                    
                elif self.type_paiement == 'DETTE':
                    self.montant_paye = 0
                    self.reste_a_payer = self.prix_total
                    if self.client:
                        self.client.solde -= self.prix_total
                        self.client.save()
                        
                elif self.type_paiement == 'ACOMPTE':
                    self.reste_a_payer = self.prix_total - self.montant_paye
                    if self.client and self.reste_a_payer > 0:
                        self.client.solde -= self.reste_a_payer
                        self.client.save()
            
            # Mise à jour du stock
            self.produit.stock_actuel -= self.quantite_sacs
            self.produit.save()
            
        super().save(*args, **kwargs)

class Paiement(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='paiements')
    date_paiement = models.DateTimeField(auto_now_add=True)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    commentaire = models.CharField(max_length=255, blank=True, default="Versement")
    type_versement = models.CharField(max_length=20, choices=[
        ('REMBOURSEMENT', 'Remboursement de dette'),
        ('AVANCE', 'Avance sur futurs achats'),
    ], default='AVANCE')

    def save(self, *args, **kwargs):
        if not self.pk:
            montant_restant = self.montant
            
            # ÉTAPE 1: Rembourser d'abord les dettes existantes
            if self.client.solde < 0:
                dette_actuelle = abs(self.client.solde)
                
                if montant_restant >= dette_actuelle:
                    # Le paiement couvre toute la dette
                    self.client.solde = 0
                    self.type_versement = 'REMBOURSEMENT'
                    montant_restant -= dette_actuelle
                    commentaire_dette = f"Remboursement total de dette: {dette_actuelle} GNF"
                    
                    # ✅ MARQUER TOUTES LES DETTES DU CLIENT COMME PAYÉES
                    ventes_dette = Vente.objects.filter(
                        client=self.client, 
                        type_paiement='DETTE',
                        reste_a_payer__gt=0
                    )
                    for vente in ventes_dette:
                        vente.reste_a_payer = 0
                        vente.type_paiement = 'COMPTANT'  # Changement du statut
                        vente.save()
                        commentaire_dette += f" Vente #{vente.id} remboursée."
                    
                    # ✅ AUSSI POUR LES ACOMPTES (cas de Fatim)
                    ventes_acompte = Vente.objects.filter(
                        client=self.client, 
                        type_paiement='ACOMPTE',
                        reste_a_payer__gt=0
                    )
                    for vente in ventes_acompte:
                        vente.reste_a_payer = 0
                        vente.type_paiement = 'COMPTANT'  # L'acompte devient comptant
                        vente.save()
                        commentaire_dette += f" Acompte #{vente.id} soldé."
                    
                else:
                    # Le paiement ne couvre qu'une partie de la dette
                    self.client.solde += montant_restant
                    self.type_versement = 'REMBOURSEMENT'
                    
                    # Trouver une vente à rembourser partiellement (d'abord les dettes, puis les acomptes)
                    vente_a_rembourser = Vente.objects.filter(
                        client=self.client, 
                        type_paiement='DETTE',
                        reste_a_payer__gt=0
                    ).first()
                    
                    if not vente_a_rembourser:
                        vente_a_rembourser = Vente.objects.filter(
                            client=self.client, 
                            type_paiement='ACOMPTE',
                            reste_a_payer__gt=0
                        ).first()
                    
                    if vente_a_rembourser:
                        vente_a_rembourser.reste_a_payer -= montant_restant
                        if vente_a_rembourser.reste_a_payer == 0:
                            vente_a_rembourser.type_paiement = 'COMPTANT'
                        vente_a_rembourser.save()
                        commentaire_dette = f"Remboursement partiel de {montant_restant} GNF sur vente #{vente_a_rembourser.id}"
                    
                    montant_restant = 0
                
                self.commentaire = f"{commentaire_dette}. {self.commentaire}"
            
            # ÉTAPE 2: S'il reste de l'argent, ça devient une avance
            if montant_restant > 0:
                self.client.solde += montant_restant
                if self.type_versement == 'REMBOURSEMENT':
                    self.commentaire += f" + Avance restante: {montant_restant} GNF"
            
            self.client.save()
            
        super().save(*args, **kwargs)