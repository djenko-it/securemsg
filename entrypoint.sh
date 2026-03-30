#!/bin/sh
# Entrypoint script to start the Flask application

# Créer le répertoire de données s'il n'existe pas
mkdir -p /app/data

# Initialiser la base de données uniquement si elle n'existe pas
if [ ! -f "/app/data/messages.db" ]; then
    python -c "from app import init_db; init_db()"
fi

# Start the Flask application
exec "$@"
