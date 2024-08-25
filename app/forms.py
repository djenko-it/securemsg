from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class SendMessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=1, max=1000)])
    expiry = SelectField('Durée de validité', choices=[('3h', '3 heures'), ('1d', '1 jour'), ('1w', '1 semaine'), ('1m', '1 mois')], validators=[DataRequired()])
    delete_on_read = BooleanField('Supprimer après lecture')
    password_protect = BooleanField('Protéger par mot de passe')
    password = PasswordField('Mot de passe', validators=[Length(max=100)])
    submit = SubmitField('Envoyer')

class PasswordForm(FlaskForm):
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Envoyer')
