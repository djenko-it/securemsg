# SecureMsg

**SecureMsg** est une application web sécurisée pour l'envoi de messages chiffrés. Chaque message est protégé par un lien unique et peut être configuré pour être supprimé après lecture ou après une certaine durée.

## Fonctionnalités

- **Chiffrement AES-256** : Les messages sont chiffrés avec AES-256 en mode GCM.
- **Suppression après lecture** : Option pour supprimer automatiquement le message après lecture.
- **Protection par mot de passe** : Option pour protéger le message par un mot de passe.
- **Expiration automatique** : Les messages peuvent expirer après 3 heures, 1 jour, 1 semaine ou 1 mois.
- **Interface responsive** : Utilisation de Tailwind CSS et Bootstrap pour une interface moderne et adaptée à tous les appareils.

## Prérequis

- Docker
- Docker Compose

## Installation

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/votre-utilisateur/securemsg.git
   cd securemsg
   ```

2. Configurez les variables d'environnement dans le fichier `.env` :
   ```env
   FLASK_ENV=development
   SOFTWARE_NAME=SecureMsg
   SHOW_DELETE_ON_READ=true
   SHOW_PASSWORD_PROTECT=true
   CONTACT_EMAIL=djenko-it@protonmail.com
   TITLE_SEND_MESSAGE="Envoyer un Message Sécurisé"
   TITLE_READ_MESSAGE="Lire le Message"
   SECRET_KEY=supersecretkey
   REDIS_URL="redis://redis:6379/0"
   ENCRYPTION_KEY="l2dZjMxBI4kkHozizxvMDSm6rKbNmT3ZBvV9NQ6KUlk="
   ```

3. Construisez et lancez les conteneurs Docker :
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. Accédez à l'application à l'adresse suivante :
   ```
   http://localhost:5000
   ```

## Utilisation

1. **Envoyer un message** :
   - Remplissez le formulaire avec votre message.
   - Configurez les options de suppression après lecture, de protection par mot de passe et d'expiration.
   - Cliquez sur "Envoyer" pour générer un lien unique.

2. **Lire un message** :
   - Accédez au lien unique généré.
   - Si le message est protégé par un mot de passe, entrez le mot de passe pour le déchiffrer.

## Configuration

Les paramètres de l'application peuvent être configurés via les variables d'environnement dans le fichier `.env` ou directement dans la base de données SQLite.

## Contribution

Les contributions sont les bienvenues. Veuillez ouvrir une issue ou une pull request pour toute suggestion ou correction.

