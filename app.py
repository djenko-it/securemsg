import os
import uuid
import base64
import sqlite3
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
DATABASE = '/app/messages.db'

# Définition de PasswordForm
class PasswordForm(FlaskForm):
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Envoyer')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=10, check_same_thread=False)
    return db

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('DROP TABLE IF EXISTS messages')
        conn.execute('''
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                message TEXT,
                expiry TIMESTAMP,
                delete_on_read BOOLEAN,
                password TEXT,
                views INTEGER DEFAULT 0
            )
        ''')
        conn.execute('DROP TABLE IF EXISTS settings')
        conn.execute('''
            CREATE TABLE settings (
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
        conn.execute('''
            INSERT INTO settings (software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect, contact_email, title_send_message, title_read_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            os.environ.get('SOFTWARE_NAME', 'SecureMsg'),
            os.environ.get('DELETE_ON_READ_DEFAULT', 'false').lower() == 'true',
            os.environ.get('PASSWORD_PROTECT_DEFAULT', 'false').lower() == 'true',
            os.environ.get('SHOW_DELETE_ON_READ', 'true').lower() == 'true',
            os.environ.get('SHOW_PASSWORD_PROTECT', 'true').lower() == 'true',
            os.environ.get('CONTACT_EMAIL', 'djenko-it@protonmail.com'),
            os.environ.get('TITLE_SEND_MESSAGE', 'Envoyer un Message Sécurisé'),
            os.environ.get('TITLE_READ_MESSAGE', 'Lire le Message')
        ))

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

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

def encrypt_message(message, key):
    key = key[:32]  # Prendre les 32 premiers caractères pour une clé de 128 bits
    backend = default_backend()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key.encode()), modes.CFB(iv), backend=backend)
    encryptor = cipher.encryptor()
    ct = encryptor.update(message.encode()) + encryptor.finalize()
    return base64.urlsafe_b64encode(iv + ct).decode()

def decrypt_message(encrypted_message, key):
    key = key[:32]  # Prendre les 32 premiers caractères pour une clé de 128 bits
    backend = default_backend()
    encrypted_message = base64.urlsafe_b64decode(encrypted_message)
    iv = encrypted_message[:16]
    cipher = Cipher(algorithms.AES(key.encode()), modes.CFB(iv), backend=backend)
    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(encrypted_message[16:]) + decryptor.finalize()
    return decrypted_message.decode()

@app.route('/')
def index():
    settings = get_settings()
    return render_template('index.html', settings=settings)

@app.route('/send', methods=['POST'])
def send_message():
    settings = get_settings()
    message = request.form['message']

    # Génération de l'UUID qui sert d'identifiant et de clé de chiffrement
    encryption_key = str(uuid.uuid4())

    # Chiffrement du message avec l'UUID
    encrypted_message = encrypt_message(message, encryption_key)

    # Récupérer les options depuis le formulaire
    delete_on_read = 'delete_on_read' in request.form if 'delete_on_read' in request.form else settings['delete_on_read_default']
    password_protect = 'password_protect' in request.form if 'password_protect' in request.form else settings['password_protect_default']
    password = request.form['password'] if password_protect else None
    hashed_password = generate_password_hash(password) if password else None

    # Stockage du message chiffré dans la base de données
    message_id = encryption_key
    expiry_option = request.form['expiry']
    expiry_time = get_expiry_time(expiry_option)

    with sqlite3.connect(DATABASE) as conn:
        conn.execute('INSERT INTO messages (id, message, expiry, delete_on_read, password) VALUES (?, ?, ?, ?, ?)', 
                     (message_id, encrypted_message, expiry_time, delete_on_read, hashed_password))
    
    # Génération du lien à partager
    link = url_for('view_message', message_id=message_id, _external=True)
    return render_template('index.html', settings=settings, message_link=link)


@app.route('/message/<message_id>', methods=['GET', 'POST'])
def view_message(message_id):
    settings = get_settings()
    
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('SELECT message, expiry, delete_on_read, password, views FROM messages WHERE id = ?', (message_id,))
        row = cur.fetchone()

        if row:
            encrypted_message, expiry, delete_on_read, hashed_password, views = row

            # Déchiffrement du message avec l'UUID
            try:
                message = decrypt_message(encrypted_message, message_id)
            except Exception as e:
                flash("Erreur de déchiffrement. Le lien est peut-être incorrect.")
                return redirect(url_for('message_not_found'))

            form = PasswordForm()
            if request.method == 'POST':
                if form.validate_on_submit():
                    password = form.password.data
                    if hashed_password and not check_password_hash(hashed_password, password):
                        flash("Mot de passe incorrect.")
                        return render_template('password_required.html', message_id=message_id, form=form, settings=settings)
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                    else:
                        views += 1
                        conn.execute('UPDATE messages SET views = ? WHERE id = ?', (views, message_id))
                    return render_template('view_message.html', message=message, expiry=expiry, delete_on_read=delete_on_read, settings=settings, views=views)
            else:
                if hashed_password:
                    return render_template('password_required.html', message_id=message_id, form=form, settings=settings)
                else:
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                    else:
                        views += 1
                        conn.execute('UPDATE messages SET views = ? WHERE id = ?', (views, message_id))
                    return render_template('view_message.html', message=message, expiry=expiry, delete_on_read=delete_on_read, settings=settings, views=views)
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
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
