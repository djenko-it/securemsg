#!/bin/sh
# Script pour compiler le CSS avec Tailwind localement

# Installer les dépendances si nécessaire
if [ ! -d "node_modules" ]; then
    npm install
fi

# Compiler le CSS avec Tailwind
npx tailwindcss -i ./src/tailwind.css -o ./static/css/tailwind.css

echo "CSS compilé avec succès !"