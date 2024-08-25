from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import get_settings, encrypt_message, decrypt_message, save_message, get_message
from .forms import PasswordForm, SendMessageForm

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
def index():
    settings = get_settings()
    return render_template('index.html', settings=settings)

@main_blueprint.route('/send', methods=['POST'])
def send_message():
    form = SendMessageForm()
    if form.validate_on_submit():
        # Logique d'envoi du message...
        pass
    return render_template('index.html', form=form)

@main_blueprint.route('/message/<message_id>', methods=['GET', 'POST'])
def view_message(message_id):
    # Logique de visualisation du message...
    pass
