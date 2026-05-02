# SecureMsg

**Application web sécurisée pour envoyer des messages auto-détruits.**

---

## Fonctionnalités

- **Chiffrement AES-256** – Messages chiffrés de bout en bout
- **Suppression automatique** – Suppression après lecture ou à l'expiration
- **Protection par mot de passe** – Optionnelle pour une sécurité renforcée
- **Expiration programmable** – 3h, 1 jour, 1 semaine ou 1 mois
- **QR Code** – Partage simplifié via code QR
- **Historique** – Suivi de vos messages envoyés

---

## Installation

### Prérequis
- Docker + Docker Compose

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/djenko-it/securemsg.git
cd securemsg

# 2. Configurer (optionnel)
# Éditer .env pour personnaliser (nom, email, clé de chiffrement, etc.)

# 3. Lancer
docker-compose up -d

# 4. Accéder à l'application
# http://localhost:5000
```

---

## Utilisation

### Envoyer un message
1. Écrivez votre message
2. Choisissez les options (expiration, mot de passe)
3. Cliquez sur **Envoyer** → un lien unique est généré
4. Partagez le lien ou le QR code

### Lire un message
1. Ouvrez le lien reçu
2. Entrez le mot de passe si demandé
3. Le message s'affiche et peut être copié

### Voir l'historique
- Cliquez sur **Mes messages** dans la navbar
- Liste de tous vos messages avec statut (lu/non lu/expiré)
- Possibilité de supprimer manuellement

---

## Configuration

| Variable | Description | Valeur par défaut |
|----------|-------------|------------------|
| `SECRET_KEY` | Clé secrète Flask | `supersecretkey_changez_moi_en_production` |
| `ENCRYPTION_KEY` | Clé de chiffrement AES-256 | Générée automatiquement |
| `SOFTWARE_NAME` | Nom de l'application | `SecureMsg` |
