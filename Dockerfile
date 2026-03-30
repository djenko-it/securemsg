# Étape 1 : Utiliser une image Python Alpine comme base
FROM python:3.12.7-alpine

# Étape 2 : Installer les dépendances système
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    nodejs \
    npm \
    build-base \
    git

# Étape 3 : Définir le répertoire de travail
WORKDIR /app

# Étape 4 : Copier les fichiers nécessaires pour installer les dépendances
COPY requirements.txt ./
COPY package*.json ./
COPY src/ ./src/
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install

# Étape 5 : Compiler le CSS avec Tailwind
RUN npx tailwindcss -i ./src/tailwind.css -o ./static/css/tailwind.css

# Étape 6 : Copier le reste de l'application
COPY . .

# Étape 7 : Nettoyer les fichiers inutiles pour réduire la taille
RUN apk del --no-cache gcc musl-dev libffi-dev build-base python3-dev && \
    rm -rf /var/cache/apk/* /root/.cache /tmp/*

# Étape 8 : Copier le script d'entrée et définir les permissions
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Étape 9 : Exposer le port sur lequel l'application fonctionnera
EXPOSE 5000

# Étape 10 : Définir les variables d'environnement par défaut
ENV SOFTWARE_NAME=SecureMsg
ENV SHOW_DELETE_ON_READ=true
ENV SHOW_PASSWORD_PROTECT=true
ENV CONTACT_EMAIL=djenko-it@protonmail.com
ENV TITLE_SEND_MESSAGE="Envoyer un Message Sécurisé"
ENV TITLE_READ_MESSAGE="Lire le Message"

# Étape 11 : Utiliser le script d'entrée
ENTRYPOINT ["/entrypoint.sh"]

# Étape 12 : Lancer l'application avec Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]