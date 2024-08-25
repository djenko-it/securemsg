import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

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
