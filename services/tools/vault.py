import json
import os
import base64
from hashlib import sha256

VAULT_PATH = os.path.join(os.path.dirname(__file__), 'vault.enc')
KEY_PATH = os.path.join(os.path.dirname(__file__), '.vault_key')

def _get_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'rb') as f:
            return f.read()
    else:
        key = os.urandom(32)
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        return key

def _xor_encrypt_decrypt(data: bytes, key: bytes) -> bytes:
    key_hash = sha256(key).digest()
    return bytes(a ^ key_hash[i % len(key_hash)] for i, a in enumerate(data))

def get_credentials():
    if not os.path.exists(VAULT_PATH):
        return {}
    key = _get_key()
    with open(VAULT_PATH, 'rb') as f:
        encrypted = base64.b64decode(f.read())
    decrypted = _xor_encrypt_decrypt(encrypted, key)
    return json.loads(decrypted.decode())

def set_credential(key: str, value: str):
    creds = get_credentials()
    creds[key] = value
    vault_key = _get_key()
    encrypted = _xor_encrypt_decrypt(json.dumps(creds).encode(), vault_key)
    with open(VAULT_PATH, 'wb') as f:
        f.write(base64.b64encode(encrypted))

def get_credential(key: str, default=None):
    creds = get_credentials()
    return creds.get(key, default)