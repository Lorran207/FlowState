from datetime import UTC, datetime, timedelta
from secrets import token_hex

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return str(jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm))


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return str(jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm))


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return dict(payload)
    except JWTError:
        return None


def create_oauth_state(user_id: int | None = None) -> str:
    """JWT assinado como `state` do fluxo OAuth do GitHub.

    Stateless e com validade curta, evita CSRF no callback e carrega
    opcionalmente o usuário logado (para "conectar GitHub" na conta existente).
    """
    to_encode: dict = {
        "type": "oauth_state",
        "nonce": token_hex(8),
        "exp": datetime.now(UTC) + timedelta(minutes=10),
    }
    if user_id is not None:
        to_encode["uid"] = user_id
    return str(jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm))


def verify_oauth_state(state: str) -> int | None:
    """Valida o state do OAuth. Retorna o user_id embutido ou None se válido sem usuário.

    Levanta ValueError se o state for inválido/expirado.
    """
    payload = decode_token(state)
    if not payload or payload.get("type") != "oauth_state":
        raise ValueError("Invalid OAuth state")
    uid = payload.get("uid")
    return int(uid) if uid is not None else None
