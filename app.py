from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'  # Assurez-vous d'avoir une clé secrète
csrf = CSRFProtect(app)

# Configuration des paramètres globaux
class Settings:
    software_name = "SecureMsg"
    title_send_message = "Envoyer un Message Sécurisé"
    title_read_message = "Lire le Message"
    contact_email = "djenko-it@protonmail.com"
    show_delete_on_read = True
    show_password_protect = True

settings = Settings()

# Modèle de message
class Message:
    def __init__(self, content, expiry, delete_on_read, password_protected, password):
        self.id = str(uuid.uuid4())
        self.content = content
        self.expiry = expiry
        self.delete_on_read = delete_on_read
        self.password_protected = password_protected
        self.password = password
        self.created_at = datetime.now()

# Base de données fictive pour stocker les messages
db = {}

# Formulaire de mot de passe
class PasswordForm(FlaskForm):
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Envoyer')

# Fonction pour calculer la durée de validité restante
def calculate_validity_duration(expiry):
    remaining_time = expiry - datetime.now()
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        content = request.form['message']
        expiry_duration = request.form['expiry']
        delete_on_read = 'delete_on_read' in request.form
        password_protected = 'password_protect' in request.form
        password = request.form['password'] if password_protected else None

        # Calculer la date d'expiration
        if expiry_duration == '3h':
            expiry = datetime.now() + timedelta(hours=3)
        elif expiry_duration == '1d':
            expiry = datetime.now() + timedelta(days=1)
        elif expiry_duration == '1w':
            expiry = datetime.now() + timedelta(weeks=1)
        elif expiry_duration == '1m':
            expiry = datetime.now() + timedelta(days=30)

        message = Message(content, expiry, delete_on_read, password_protected, password)
        db[message.id] = message
        flash(f"Message créé : {url_for('view_message', message_id=message.id, _external=True)}", 'success')
        return redirect(url_for('index'))

    return render_template('index.html', settings=settings)

@app.route('/message/<message_id>', methods=['GET', 'POST'])
def view_message(message_id):
    message = db.get(message_id)
    if not message:
        return render_template('message_not_found.html', settings=settings), 404

    if message.expiry < datetime.now():
        db.pop(message_id, None)
        return render_template('message_expired.html', settings=settings), 410

    form = PasswordForm()
    if message.password_protected:
        if form.validate_on_submit():
            if form.password.data == message.password:
                if message.delete_on_read:
                    db.pop(message_id, None)
                validity_duration = calculate_validity_duration(message.expiry)
                return render_template('view_message.html', message=message.content, delete_on_read=message.delete_on_read, validity_duration=validity_duration, settings=settings)
            else:
                flash("Mot de passe incorrect", 'danger')
        return render_template('password_required.html', form=form, settings=settings)

    if message.delete_on_read:
        db.pop(message_id, None)
    validity_duration = calculate_validity_duration(message.expiry)
    return render_template('view_message.html', message=message.content, delete_on_read=message.delete_on_read, validity_duration=validity_duration, settings=settings)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('message_not_found.html', settings=settings), 404

if __name__ == '__main__':
    app.run(debug=True)
