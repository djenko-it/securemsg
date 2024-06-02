#!/bin/sh
# Entrypoint script to build CSS and start the Flask application

# Créer le dossier static/css s'il n'existe pas
mkdir -p static/css

# Construire le CSS avec Tailwind
npm run build:css

# Vérifier que le fichier CSS est généré
if [ ! -f static/css/tailwind.css ]; then
  echo "Erreur : Le fichier CSS n'a pas été généré"
  exit 1
fi

# Démarrer l'application Flask
exec "$@"
