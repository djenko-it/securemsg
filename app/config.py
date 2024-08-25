import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    DATABASE = os.environ.get('DATABASE_URL', '/app/messages.db')
    # Autres configurations
