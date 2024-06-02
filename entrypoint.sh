#!/bin/sh
# Entrypoint script to build CSS and start the Flask application

# Build the Tailwind CSS
npm run build:css

# Start the Flask application
exec "$@"
