#!/bin/sh
# Entrypoint script to start the Flask application

# Créer le répertoire de données s'il n'existe pas
mkdir -p /app/data

# Vérifier que le répertoire a les bonnes permissions
chmod -R 777 /app/data 2>/dev/null || true

# Initialiser la base de données
# Note: init_db() est maintenant idempotent et ne détruit pas les données existantes
python -c "from app import init_db; init_db()"

# Générer une ENCRYPTION_KEY si elle n'est pas définie dans l'environnement
# et que la base de données vient d'être créée
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "WARNING: ENCRYPTION_KEY non définie. Veuillez la configurer dans le fichier .env pour la production."
fi

# Start the Flask application
exec "$@"
