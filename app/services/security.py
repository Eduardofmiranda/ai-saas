import os
import sys
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_secret


_SECRET_KEY = get_secret("SECRET_KEY")
if not _SECRET_KEY:
    print(
        "\n[FATAL] SECRET_KEY nao esta configurado no ambiente.\n"
        "Defina a variavel SECRET_KEY no .env antes de iniciar o servidor.\n",
        file=sys.stderr,
    )
    sys.exit(1)


def hash_password(raw_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    algorithm = get_secret("ALGORITHM", "HS256")
    minutes = int(get_secret("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _SECRET_KEY, algorithm=algorithm)


def decode_access_token(token: str) -> dict | None:
    algorithm = get_secret("ALGORITHM", "HS256")
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[algorithm])
    except JWTError:
        return None
