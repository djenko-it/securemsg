#!/bin/sh
# Entrypoint script to build CSS and start the Flask application

# Build the Tailwind CSS
npm run build:css

# Initialiser la base de données
python -c "from app import init_db; init_db()"

# Start the Flask application
exec "$@"
