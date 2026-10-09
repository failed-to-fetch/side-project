import os

from cryptography.fernet import Fernet

_fernet = Fernet(os.environ["TOKEN_ENCRYPTION_KEY"])


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()