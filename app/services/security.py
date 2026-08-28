import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_secret


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
    secret = get_secret("SECRET_KEY", "dev-secret")
    algorithm = get_secret("ALGORITHM", "HS256")
    minutes = int(get_secret("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict | None:
    secret = get_secret("SECRET_KEY", "dev-secret")
    algorithm = get_secret("ALGORITHM", "HS256")
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        return None
