import json
import os
from cryptography.fernet import Fernet

VAULT_PATH = os.path.join(os.path.dirname(__file__), 'vault.enc')
KEY_PATH = os.path.join(os.path.dirname(__file__), '.vault_key')

def _get_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        return key

def _get_cipher():
    return Fernet(_get_key())

def get_credentials():
    if not os.path.exists(VAULT_PATH):
        return {}
    cipher = _get_cipher()
    with open(VAULT_PATH, 'rb') as f:
        encrypted = f.read()
    decrypted = cipher.decrypt(encrypted)
    return json.loads(decrypted.decode())

def set_credential(key: str, value: str):
    creds = get_credentials()
    creds[key] = value
    cipher = _get_cipher()
    encrypted = cipher.encrypt(json.dumps(creds).encode())
    with open(VAULT_PATH, 'wb') as f:
        f.write(encrypted)

def get_credential(key: str, default=None):
    creds = get_credentials()
    return creds.get(key, default)