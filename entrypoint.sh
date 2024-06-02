#!/bin/sh
# Entrypoint script to build CSS and start the Flask application

# Créer le dossier static/css s'il n'existe pas
mkdir -p static/css

# Construire le CSS avec Tailwind
npm run build:css

# Démarrer l'application Flask
exec "$@"
