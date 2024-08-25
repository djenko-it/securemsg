from flask import Flask
from .config import Config
from .routes import main_blueprint
from .models import init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialiser la base de données
    with app.app_context():
        init_db()

    # Enregistrer les blueprints
    app.register_blueprint(main_blueprint)

    return app
