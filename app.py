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
        db = g._database = sqlite3.connect(DATABASE)
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
                show_password_protect BOOLEAN
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
            INSERT INTO settings (software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect)
            VALUES (?, ?, ?, ?, ?)
        ''', ("SecureMsg", False, False, True, True))
        # Insert default admin
        conn.execute('''
            INSERT INTO admin (username, password, must_change_password)
            VALUES (?, ?, ?)
        ''', ("admin", generate_password_hash("admin"), True))

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_settings():
    db = get_db()
    cur = db.execute('SELECT software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect FROM settings WHERE id = 1')
    settings = cur.fetchone()
    return {
        'software_name': settings[0],
        'delete_on_read_default': settings[1],
        'password_protect_default': settings[2],
        'show_delete_on_read': settings[3],
        'show_password_protect': settings[4]
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

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    settings = get_settings()  # Fetch settings here
    if request.method == 'POST':
        software_name = request.form['software_name']
        delete_on_read_default = 'delete_on_read_default' in request.form
        password_protect_default = 'password_protect_default' in request.form
        show_delete_on_read = 'show_delete_on_read' in request.form
        show_password_protect = 'show_password_protect' in request.form
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('''
                UPDATE settings
                SET software_name = ?, delete_on_read_default = ?, password_protect_default = ?, show_delete_on_read = ?, show_password_protect = ?
                WHERE id = 1
            ''', (software_name, delete_on_read_default, password_protect_default, show_delete_on_read, show_password_protect))
        flash('Paramètres mis à jour avec succès')
        return redirect(url_for('admin'))
    else:
        return render_template('admin.html', settings=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = get_settings()  # Fetch settings here
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cur = db.execute('SELECT id, password, must_change_password FROM admin WHERE username = ?', (username,))
        admin = cur.fetchone()
        if admin and check_password_hash(admin[1], password):
            session['logged_in'] = True
            session['admin_id'] = admin[0]
            if admin[2]:  # Must change password
                return redirect(url_for('change_password'))
            return redirect(url_for('admin'))
        flash('Nom d’utilisateur ou mot de passe incorrect')
    return render_template('login.html', settings=settings)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    settings = get_settings()  # Fetch settings here
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            hashed_password = generate_password_hash(new_password)
            with sqlite3.connect(DATABASE) as conn:
                conn.execute('''
                    UPDATE admin
                    SET password = ?, must_change_password = 0
                    WHERE id = ?
                ''', (hashed_password, session['admin_id']))
            flash('Mot de passe changé avec succès')
            return redirect(url_for('admin'))
        else:
            flash('Les mots de passe ne correspondent pas')
    return render_template('change_password.html', settings=settings)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('admin_id', None)
    flash('Vous avez été déconnecté')
    return redirect(url_for('login'))

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

            if request.method == 'POST':
                password = request.form['password']
                if hashed_password and not check_password_hash(hashed_password, password):
                    flash("Mot de passe incorrect.")
                    return render_template('password_required.html', message_id=message_id, settings=settings)
                if delete_on_read:
                    conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings)
            else:
                if hashed_password:
                    return render_template('password_required.html', message_id=message_id, settings=settings)
                else:
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                    return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read, settings=settings)
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
