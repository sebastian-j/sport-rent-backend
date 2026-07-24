from pwdlib import PasswordHash

_password_hasher = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = _password_hasher.hash("dummy-password")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hasher.verify(password, hashed_password)
