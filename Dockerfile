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

# Copier le script d'entrée et définir les permissions
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exposer le port sur lequel l'application fonctionnera
EXPOSE 5000

# Définir les variables d'environnement par défaut
ENV SOFTWARE_NAME=SecureMsg
ENV SHOW_DELETE_ON_READ=true
ENV SHOW_PASSWORD_PROTECT=true
ENV CONTACT_EMAIL=djenko-it@protonmail.com
ENV TITLE_SEND_MESSAGE="Envoyer un Message Sécurisé"
ENV TITLE_READ_MESSAGE="Lire le Message"

# Utiliser le script d'entrée
ENTRYPOINT ["/entrypoint.sh"]

# Lancer l'application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

