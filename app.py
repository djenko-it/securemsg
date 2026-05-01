import os
import uuid
import base64
import sqlite3
import logging
from flask import Flask, request, render_template, url_for, redirect, flash, g
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# Ajouter le filtre split pour Jinja2
@app.template_filter('split')
def split_filter(value, delimiter):
    return value.split(delimiter)

# Déterminer le chemin de la base de données
# En Docker: /app/data/messages.db
# En local: ./data/messages.db
if os.path.exists('/app'):
    DATABASE = '/app/data/messages.db'
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'messages.db')

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Générer ou récupérer la clé de chiffrement depuis l'environnement
# DOIT être une clé de 32 octets pour AES-256
# Peut être en base64 ou en string claire (sera encodée)
# IMPORTANT: Cette clé doit être la même pour tous les workers en production
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if ENCRYPTION_KEY is None:
    # En développement, générer une clé temporaire (MAIS CELA NE FONCTIONNERA PAS AVEC MULTIPLE WORKERS)
    if os.environ.get('FLASK_ENV') == 'development':
        ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()
        logger.warning("ENCRYPTION_KEY non définie. Une clé temporaire a été générée (OK pour dev single-worker).")
    else:
        raise RuntimeError(
            "ENCRYPTION_KEY doit être définie dans l'environnement pour la production. "
            'Générez-en une avec: python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"'
        )
else:
    # Vérifier la longueur de la clé
    try:
        # Essayer de décoder comme base64
        decoded = base64.urlsafe_b64decode(ENCRYPTION_KEY)
        if len(decoded) < 32:
            logger.error(f"ENCRYPTION_KEY trop courte ({len(decoded)} octets). Complétée avec des zéros.")
            ENCRYPTION_KEY = base64.urlsafe_b64encode(decoded.ljust(32, b'\x00')).decode()
    except Exception:
        # Si ce n'est pas du base64 valide, supposer que c'est une string
        if len(ENCRYPTION_KEY.encode()) < 32:
            logger.error(f"ENCRYPTION_KEY trop courte ({len(ENCRYPTION_KEY.encode())} octets). Complétée avec des zéros.")
            ENCRYPTION_KEY = ENCRYPTION_KEY.ljust(32, '\x00')

# Définition de PasswordForm pour la saisie sécurisée du mot de passe par l'utilisateur
class PasswordForm(FlaskForm):
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Envoyer')

# Fonction pour obtenir une connexion à la base de données SQLite.
# Utilisation de check_same_thread=True pour la sécurité (défaut)
# Timeout augmenté pour éviter les erreurs en cas de charge

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=30)
    return db


# Initialisation de la base de données, création des tables nécessaires
# Utilisation de IF NOT EXISTS pour éviter de détruire les données existantes

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        # Créer les tables seulement si elles n'existent pas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                message TEXT,
                encryption_key TEXT,
                expiry TIMESTAMP,
                delete_on_read BOOLEAN,
                password TEXT,
                views INTEGER DEFAULT 0
            )
        ''')
        
        # Migration: Ajouter la colonne encryption_key si elle n'existe pas
        # pour les bases de données créées avant cette mise à jour
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in cur.fetchall()]
            if 'encryption_key' not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN encryption_key TEXT")
                logger.info("Colonne encryption_key ajoutée à la table messages")
        except Exception as e:
            logger.error(f"Erreur lors de la migration de la base de données: {e}")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                software_name TEXT,
                delete_on_read_default BOOLEAN,
                password_protect_default BOOLEAN,
                show_delete_on_read BOOLEAN,
                show_password_protect BOOLEAN,
                contact_email TEXT,
                title_send_message TEXT,
                title_read_message TEXT
            )
        ''')
        # Insère les paramètres par défaut dans la table settings seulement si vide
        conn.execute('''
            INSERT OR IGNORE INTO settings 
            (id, software_name, delete_on_read_default, password_protect_default, 
             show_delete_on_read, show_password_protect, contact_email, 
             title_send_message, title_read_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            1,
            os.environ.get('SOFTWARE_NAME', 'SecureMsg'),
            os.environ.get('DELETE_ON_READ_DEFAULT', 'false').lower() == 'true',
            os.environ.get('PASSWORD_PROTECT_DEFAULT', 'false').lower() == 'true',
            os.environ.get('SHOW_DELETE_ON_READ', 'true').lower() == 'true',
            os.environ.get('SHOW_PASSWORD_PROTECT', 'true').lower() == 'true',
            os.environ.get('CONTACT_EMAIL', 'djenko-it@protonmail.com'),
            os.environ.get('TITLE_SEND_MESSAGE', 'Envoyer un Message Sécurisé'),
            os.environ.get('TITLE_READ_MESSAGE', 'Lire le Message')
        ))
        logger.info("Base de données initialisée avec succès (tables vérifiées/existantes)")

# Initialisation de la base de données au démarrage de l'application
init_db()

# Fermeture de la connexion à la base de données après chaque requête.
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Récupère les paramètres de configuration de l'application à partir de la base de données.
def get_settings():
    db = get_db()
    cur = db.execute('SELECT software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect, contact_email, title_send_message, title_read_message FROM settings WHERE id = 1')
    settings = cur.fetchone()
    return {
        'software_name': settings[0],
        'delete_on_read_default': settings[1],
        'password_protect_default': settings[2],
        'show_delete_on_read': settings[3],
        'show_password_protect': settings[4],
        'contact_email': settings[5],
        'title_send_message': settings[6],
        'title_read_message': settings[7]
    }

# Détermine le délai d'expiration du message en fonction de l'option choisie par l'utilisateur.
def get_expiry_time(expiry_option):
    if expiry_option == '3h':
        return datetime.now() + timedelta(hours=3)
    elif expiry_option == '1d':
        return datetime.now() + timedelta(days=1)
    elif expiry_option == '1w':
        return datetime.now() + timedelta(weeks=1)
    elif expiry_option == '1m':
        return datetime.now() + timedelta(days=30)
    return None

# Calcule la durée restante avant l'expiration d'un message.
def calculate_validity_duration(expiry_time):
    remaining_time = expiry_time - datetime.now()
    days = remaining_time.days
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days} jours, {hours} heures, {minutes} minutes"
    elif hours > 0:
        return f"{hours} heures, {minutes} minutes"
    elif minutes > 0:
        return f"{minutes} minutes"
    else:
        return f"{seconds} secondes"

def encrypt_message(message, key):
    """
    Chiffre un message avec AES-256-GCM.
    
    Args:
        message: Le message à chiffrer (string)
        key: La clé de chiffrement (string ou bytes). Doit faire 32 octets.
    
    Returns:
        Le message chiffré en base64 (string)
    """
    # Convertir la clé en bytes si c'est une string
    if isinstance(key, str):
        key_bytes = key.encode()[:32]  # Limite à 32 octets
    else:
        key_bytes = key[:32]  # Limite à 32 octets
    
    # Si la clé est trop courte, la compléter avec des zéros (DEVRAIT NE JAMAIS ARRIVER)
    if len(key_bytes) < 32:
        logger.error(f"Clé de chiffrement trop courte: {len(key_bytes)} octets. Complétée avec des zéros.")
        key_bytes = key_bytes.ljust(32, b'\x00')
    
    iv = os.urandom(12)  # GCM nécessite un IV de 96 bits.
    cipher = Cipher(algorithms.AES(key_bytes), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message.encode()) + encryptor.finalize()
    return base64.urlsafe_b64encode(iv + encryptor.tag + ciphertext).decode()

def decrypt_message(encrypted_message, key):
    """
    Déchiffre un message avec AES-256-GCM.
    
    Args:
        encrypted_message: Le message chiffré en base64 (string)
        key: La clé de déchiffrement (string ou bytes). Doit faire 32 octets.
    
    Returns:
        Le message déchiffré (string)
    
    Raises:
        Exception: En cas d'erreur de déchiffrement
    """
    # Convertir la clé en bytes si c'est une string
    if isinstance(key, str):
        key_bytes = key.encode()[:32]  # Limite à 32 octets
    else:
        key_bytes = key[:32]  # Limite à 32 octets
    
    # Si la clé est trop courte, la compléter avec des zéros
    if len(key_bytes) < 32:
        logger.error(f"Clé de déchiffrement trop courte: {len(key_bytes)} octets. Complétée avec des zéros.")
        key_bytes = key_bytes.ljust(32, b'\x00')
    
    decoded_message = base64.urlsafe_b64decode(encrypted_message)
    iv = decoded_message[:12]  # Le IV est dans les 12 premiers octets.
    tag = decoded_message[12:28]  # Le tag GCM est sur 16 octets.
    ciphertext = decoded_message[28:]  # Le reste est le texte chiffré.
    cipher = Cipher(algorithms.AES(key_bytes), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode()

# Route pour afficher la page d'accueil et les paramètres de configuration.
@app.route('/')
def index():
    settings = get_settings()
    return render_template('index.html', settings=settings)

@app.route('/send', methods=['POST'])
def send_message():
    settings = get_settings()
    message = request.form['message']

    # Génération d'un UUID comme identifiant unique du message
    message_id = str(uuid.uuid4())
    
    # Génération d'une clé de chiffrement aléatoire unique pour ce message
    # Cette clé est stockée chiffrée avec la clé maître (ENCRYPTION_KEY)
    message_encryption_key = os.urandom(32)  # 32 octets pour AES-256
    
    # Chiffrement du message avec la clé aléatoire
    encrypted_message = encrypt_message(message, message_encryption_key)
    
    # Chiffrement de la clé du message avec la clé maître
    # On encode la clé binaire en base64 pour la stocker comme string
    # puis on la chiffré avec la clé maître
    encrypted_key = encrypt_message(base64.urlsafe_b64encode(message_encryption_key).decode(), ENCRYPTION_KEY)

    # Récupérer les options depuis le formulaire
    # Si la checkbox est cochée, elle est dans request.form. Sinon, utiliser la valeur par défaut.
    delete_on_read = 'delete_on_read' in request.form or settings['delete_on_read_default']
    password_protect = 'password_protect' in request.form or settings['password_protect_default']
    password = request.form['password'] if password_protect else None
    hashed_password = generate_password_hash(password) if password else None

    # Stockage du message chiffré dans la base de données
    expiry_option = request.form['expiry']
    expiry_time = get_expiry_time(expiry_option)

    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            'INSERT INTO messages (id, message, encryption_key, expiry, delete_on_read, password) VALUES (?, ?, ?, ?, ?, ?)', 
            (message_id, encrypted_message, encrypted_key, expiry_time, delete_on_read, hashed_password)
        )
    
    # Génération du lien à partager
    link = url_for('view_message', message_id=message_id, _external=True)
    return render_template('index.html', settings=settings, message_link=link)


@app.route('/message/<message_id>', methods=['GET', 'POST'])
def view_message(message_id):
    settings = get_settings()
    
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('SELECT message, encryption_key, expiry, delete_on_read, password, views FROM messages WHERE id = ?', (message_id,))
        row = cur.fetchone()

        if row:
            encrypted_message, encrypted_key, expiry, delete_on_read, hashed_password, views = row

            # Calcul de la durée de validité restante
            expiry_time = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S.%f')
            
            # Vérifier si le message a expiré
            if expiry_time < datetime.now():
                # Supprimer le message expiré
                conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                logger.info(f"Message {message_id} expiré et supprimé")
                return redirect(url_for('message_expired'))
            
            time_remaining_str = calculate_validity_duration(expiry_time)

            # Déchiffrer la clé du message avec la clé maître
            try:
                # La clé du message est stockée chiffrée en base64
                encrypted_key_b64 = decrypt_message(encrypted_key, ENCRYPTION_KEY)
                # Décoder la clé du message depuis base64
                message_encryption_key = base64.urlsafe_b64decode(encrypted_key_b64.encode())
                # Déchiffrer le message avec la clé du message
                message = decrypt_message(encrypted_message, message_encryption_key)
            except Exception as e:
                logger.error(f"Erreur de déchiffrement pour le message {message_id}: {e}")
                flash("Erreur de déchiffrement. Le lien est peut-être incorrect ou le message a été corrompu.")
                return redirect(url_for('message_not_found'))

            form = PasswordForm()
            if request.method == 'POST':
                if form.validate_on_submit():
                    password = form.password.data
                    if hashed_password and not check_password_hash(hashed_password, password):
                        flash("Mot de passe incorrect.")
                        return render_template('password_required.html', message_id=message_id, form=form, settings=settings)
                    # Mot de passe correct ou pas de protection
                    new_views = views + 1
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                        logger.info(f"Message {message_id} supprimé après lecture")
                    else:
                        conn.execute('UPDATE messages SET views = ? WHERE id = ?', (new_views, message_id))
                    return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings, views=new_views, time_remaining=time_remaining_str)
            else:
                if hashed_password:
                    return render_template('password_required.html', message_id=message_id, form=form, settings=settings)
                else:
                    new_views = views + 1
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                        logger.info(f"Message {message_id} supprimé après lecture")
                    else:
                        conn.execute('UPDATE messages SET views = ? WHERE id = ?', (new_views, message_id))
                    return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings, views=new_views, time_remaining=time_remaining_str)
        else:
            flash("Le message n'a pas été trouvé ou a déjà été supprimé.")
            return redirect(url_for('message_not_found'))


@app.route('/message_not_found')
def message_not_found():
    settings = get_settings()
    return render_template('message_expired.html', settings=get_settings(), message_not_found=True)

@app.route('/message_expired')
def message_expired():
    settings = get_settings()
    return render_template('message_expired.html', settings=settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)