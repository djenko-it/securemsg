# Utiliser une image Python officielle comme image de base
FROM python:3.9

# Installer Node.js et npm
RUN apt-get update && apt-get install -y nodejs npm

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de l'application
COPY . /app

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer les dépendances Node.js
RUN npm install

# Construire le CSS avec Tailwind
RUN npm run build:css

# Exposer le port sur lequel l'application fonctionnera
EXPOSE 5000

# Définir les variables d'environnement par défaut
ENV SOFTWARE_NAME=SecureMsg
ENV SHOW_DELETE_ON_READ=true
ENV SHOW_PASSWORD_PROTECT=true
ENV CONTACT_EMAIL=djenko-it@protonmail.com
ENV TITLE_SEND_MESSAGE="Envoyer un Message Sécurisé"
ENV TITLE_READ_MESSAGE="Lire le Message"

# Lancer l'application
CMD ["python", "app.py"]
