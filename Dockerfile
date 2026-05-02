# Multi-stage build pour une image optimisée
# Stage 1: Builder - Compile Tailwind et installe les dépendances
FROM python:3.12.7-alpine as builder

# Installer les dépendances système pour la compilation
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    nodejs \
    npm \
    build-base \
    git

WORKDIR /app

# Copier les fichiers nécessaires pour la compilation
COPY requirements.txt ./
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY tailwind.config.js ./
COPY package.json ./
COPY package-lock.json ./

# Installer les dépendances Python
RUN pip install --no-cache-dir --user -r requirements.txt

# Installer npm et compiler Tailwind
RUN npm install && \
    npx tailwindcss -i ./src/tailwind.css -o ./static/css/tailwind.css

# Stage 2: Runtime - Image finale légère
FROM python:3.12.7-alpine

# Créer un utilisateur non-root
RUN adduser -D -u 1000 -g 1000 appuser
WORKDIR /app

# Copier les dépendances Python depuis le builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /app/static /app/static

# Copier l'application
COPY app.py ./
COPY entrypoint.sh ./
COPY .env ./
COPY templates/ templates/
RUN chmod +x ./entrypoint.sh && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/templates

# Configurer PATH pour l'utilisateur
ENV PATH=/home/appuser/.local/bin:$PATH

# Passer à l'utilisateur non-root
USER appuser

# Variables d'environnement
ENV SOFTWARE_NAME=SecureMsg
ENV SHOW_DELETE_ON_READ=true
ENV SHOW_PASSWORD_PROTECT=true
ENV CONTACT_EMAIL=djenko-it@protonmail.com
ENV TITLE_SEND_MESSAGE="Envoyer un Message Sécurisé"
ENV TITLE_READ_MESSAGE="Lire le Message"

# Nettoyer les caches
RUN rm -rf /home/appuser/.cache

# Exposer le port
EXPOSE 5000

# Script d'entrée
ENTRYPOINT ["./entrypoint.sh"]

# Commande par défaut
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "--log-level", "info", "app:app"]
