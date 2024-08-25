import sqlite3
from flask import g
from datetime import datetime

DATABASE = '/app/messages.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=10, check_same_thread=False)
    return db

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        # Création des tables...
        pass

def get_settings():
    db = get_db()
    # Récupération des paramètres...
    pass

def save_message(message_id, encrypted_message, expiry_time, delete_on_read, hashed_password):
    db = get_db()
    db.execute('INSERT INTO messages (id, message, expiry, delete_on_read, password) VALUES (?, ?, ?, ?, ?)', 
               (message_id, encrypted_message, expiry_time, delete_on_read, hashed_password))
    db.commit()

def get_message(message_id):
    db = get_db()
    # Récupération du message...
    pass
