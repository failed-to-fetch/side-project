from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # Argon2
DUMMY_HASH = _hasher.hash("not-a-real-password")

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)