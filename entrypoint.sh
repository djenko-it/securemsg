#!/bin/sh
# Entrypoint script to start the Flask application

# Initialiser la base de données uniquement si elle n'existe pas
if [ ! -f "/app/messages.db" ]; then
    python -c "from app import init_db; init_db()"
fi

# Start the Flask application
exec "$@"
