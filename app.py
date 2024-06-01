from flask import Flask, request, redirect, render_template, url_for, flash
import uuid
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Nécessaire pour les messages flash

# Configuration de la base de données
DATABASE = '/app/messages.db'

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
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/send', methods=['POST'])
def send_message():
    message = request.form['message']
    expiry_option = request.form['expiry']
    delete_on_read = 'delete_on_read' in request.form
    password_protect = 'password_protect' in request.form
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
                    return render_template('password_required.html', message_id=message_id)
                if delete_on_read:
                    conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read)
            else:
                if hashed_password:
                    return render_template('password_required.html', message_id=message_id)
                else:
                    if delete_on_read:
                        conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
                    return render_template('view_message.html', message=message, expiry=expiry_time.isoformat(), delete_on_read=delete_on_read)
        else:
            flash("Le message n'a pas été trouvé ou a déjà été consulté.")
            return redirect(url_for('message_not_found'))

@app.route('/message_not_found')
def message_not_found():
    return render_template('message_not_found.html')

@app.route('/message_expired')
def message_expired():
    return render_template('message_expired.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
