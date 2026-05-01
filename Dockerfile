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

# Étape 4 : Installer les dépendances Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Étape 5 : Copier TOUS les fichiers nécessaires pour la compilation Tailwind
# (Tailwind doit scanner les templates pour inclure les classes utilisées)
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY tailwind.config.js ./
COPY package.json ./
COPY package-lock.json ./

# Étape 6 : Installer npm et compiler Tailwind
RUN npm install && \
    npx tailwindcss -i ./src/tailwind.css -o ./static/css/tailwind.css

# Étape 7 : Copier le reste de l'application
COPY app.py ./
COPY entrypoint.sh ./
COPY docker-compose.yml ./
COPY build_css.sh ./
COPY .env ./
COPY .gitignore ./
COPY README.md ./
RUN chmod +x ./entrypoint.sh

# Étape 8 : Nettoyer les fichiers inutiles pour réduire la taille
RUN apk del --no-cache gcc musl-dev libffi-dev build-base python3-dev && \
    rm -rf /var/cache/apk/* /root/.cache /tmp/* && \
    rm -rf node_modules/ src/ package.json package-lock.json tailwind.config.js

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
ENTRYPOINT ["./entrypoint.sh"]

# Étape 12 : Lancer l'application avec Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]