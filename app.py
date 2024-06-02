import os
from flask import Flask, request, redirect, render_template, url_for, flash, session, g
import uuid
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Nécessaire pour les messages flash

# Configuration de la base de données
DATABASE = '/app/messages.db'

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
                password TEXT
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
                contact_email TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password TEXT,
                must_change_password BOOLEAN
            )
        ''')
        # Insert default settings
        conn.execute('''
            INSERT INTO settings (software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect, contact_email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            os.environ.get('SOFTWARE_NAME', 'SecureMsg'),
            os.environ.get('DELETE_ON_READ_DEFAULT', 'false').lower() == 'true',
            os.environ.get('PASSWORD_PROTECT_DEFAULT', 'false').lower() == 'true',
            os.environ.get('SHOW_DELETE_ON_READ', 'true').lower() == 'true',
            os.environ.get('SHOW_PASSWORD_PROTECT', 'true').lower() == 'true',
            os.environ.get('CONTACT_EMAIL', 'djenko-it@protonmail.com')
        ))

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_settings():
    db = get_db()
    cur = db.execute('SELECT software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect, contact_email FROM settings WHERE id = 1')
    settings = cur.fetchone()
    return {
        'software_name': settings[0],
        'delete_on_read_default': settings[1],
        'password_protect_default': settings[2],
        'show_delete_on_read': settings[3],
        'show_password_protect': settings[4],
        'contact_email': settings[5]
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

@app.route('/')
def index():
    settings = get_settings()
    return render_template('index.html', settings=settings)

@app.route('/about')
def about():
    settings = get_settings()
    return render_template('about.html', settings=settings)

@app.route('/contact')
def contact():
    settings = get_settings()
    return render_template('contact.html', settings=settings)

@app.route('/send', methods=['POST'])
def send_message():
    settings = get_settings()
    message = request.form['message']
    expiry_option = request.form['expiry']
    delete_on_read = 'delete_on_read' in request.form if 'delete_on_read' in request.form else settings['delete_on_read_default']
    password_protect = 'password_protect' in request.form if 'password_protect' in request.form else settings['password_protect_default']
    password = request.form['password'] if password_protect else None
    hashed_password = generate_password_hash(password) if password else None
    message_id = str(uuid.uuid4())
    expiry_time = get_expiry_time(expiry_option)
    
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('INSERT INTO messages (id, message, expiry, delete_on_read, password) VALUES (?, ?, ?, ?, ?)', 
                     (message_id, message, expiry_time, delete_on_read, hashed_password))
    
    link = url_for('view_message', message_id=message_id, _external=True)
    flash(link)
    return redirect(url_for('index'))

@app.route('/message/<message_id>', methods=['GET', 'POST'])
def view_message(message_id):
    settings = get_settings()  # Fetch settings here
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('SELECT message, expiry, delete_on_read, password FROM messages WHERE id = ?', (message_id,))
        row = cur.fetchone()

        if row:
            message, expiry, delete_on_read, hashed_password = row
            expiry_time = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S.%f')
            time_remaining = expiry_time - datetime.now()

            if time_remaining.total_seconds() <= 0:
                conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                flash("Le message a expiré.")
                return redirect(url_for('message_expired'))

            time_remaining_str = str(time_remaining).split('.')[0]  # Format time remaining as H:M:S

            if request.method == 'POST':
                password = request.form['password']
                if hashed_password and not check_password_hash(hashed_password, password):
                    flash("Mot de passe incorrect.")
                    return render_template('password_required.html', message_id=message_id, settings=settings)
                if delete_on_read:
                    conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings, time_remaining=time_remaining_str)
            else:
                if hashed_password:
                    return render_template('password_required.html', message_id=message_id, settings=settings)
                else:
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                    return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings, time_remaining=time_remaining_str)
        else:
            flash("Le message n'a pas été trouvé ou a déjà été consulté.")
            return redirect(url_for('message_not_found'))

@app.route('/message_not_found')
def message_not_found():
    settings = get_settings()
    return render_template('message_not_found.html', settings=settings)

@app.route('/message_expired')
def message_expired():
    settings = get_settings()
    return render_template('message_expired.html', settings=settings)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
