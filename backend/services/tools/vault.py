"""Simple encrypted credential vault."""

import json
import os
import base64
from hashlib import sha256

VAULT_PATH = os.path.join(os.path.dirname(__file__), 'vault.enc')
KEY_PATH = os.path.join(os.path.dirname(__file__), '.vault_key')


def _get_key() -> bytes:
    """Get or create vault key."""
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'rb') as f:
            return f.read()
    
    key = os.urandom(32)
    with open(KEY_PATH, 'wb') as f:
        f.write(key)
    return key


def _xor(data: bytes, key: bytes) -> bytes:
    """XOR encrypt/decrypt."""
    h = sha256(key).digest()
    return bytes(a ^ h[i % len(h)] for i, a in enumerate(data))


def get_credentials() -> dict:
    """Get all credentials."""
    if not os.path.exists(VAULT_PATH):
        return {}
    
    with open(VAULT_PATH, 'rb') as f:
        encrypted = base64.b64decode(f.read())
    return json.loads(_xor(encrypted, _get_key()).decode())


def set_credential(key: str, value: str):
    """Store credential."""
    creds = get_credentials()
    creds[key] = value
    encrypted = _xor(json.dumps(creds).encode(), _get_key())
    
    with open(VAULT_PATH, 'wb') as f:
        f.write(base64.b64encode(encrypted))


def get_credential(key: str, default=None) -> str | None:
    """Get credential by key."""
    return get_credentials().get(key, default)