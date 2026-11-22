import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt

Role = Literal["ANALISTA", "DESENVOLVEDOR"]

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "segurasaude-dev-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return dk.hex()


# Usuários sintéticos
_SALT = "segurasaude_mvp_salt"
_USERS_DB: dict[str, dict[str, str]] = {
    "analista@segurasaude.local": {
        "user_id": "usr_analista_01",
        "password_hash": _hash_password("Analista@123", _SALT),
        "role": "ANALISTA",
    },
    "dev@segurasaude.local": {
        "user_id": "usr_dev_01",
        "password_hash": _hash_password("Dev@123", _SALT),
        "role": "DESENVOLVEDOR",
    },
}


class AuthService:
    def authenticate(self, email: str, password: str) -> dict | None:
        user = _USERS_DB.get(email.strip().lower())
        if not user:
            return None

        candidate_hash = _hash_password(password, _SALT)
        if not hmac.compare_digest(candidate_hash, user["password_hash"]):
            return None

        token = self.create_access_token(
            user_id=user["user_id"],
            email=email.strip().lower(),
            role=user["role"],
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user["role"],
        }

    def create_access_token(self, user_id: str, email: str, role: Role) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=JWT_EXPIRATION_MINUTES),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
