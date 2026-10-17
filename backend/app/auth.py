"""Password hashing + signed bearer tokens. Tokens carry ONLY the user id and expiry:
roles/capabilities are always re-read from the database, never trusted from the client."""
import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, Header, HTTPException

from . import db
from .config import get_settings
from .services import authz

_ITER = 120_000


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _ITER)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
        cand = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), _ITER)
        return hmac.compare_digest(cand.hex(), dk)
    except Exception:
        return False


def _sig(payload: str) -> str:
    key = get_settings().resolved_secret().encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def make_token(user_id: str) -> str:
    exp = int(time.time()) + get_settings().vaultrag_token_ttl_seconds
    payload = base64.urlsafe_b64encode(json.dumps({"u": user_id, "e": exp}).encode()).decode()
    return f"{payload}.{_sig(payload)}"


def parse_token(token: str) -> str | None:
    try:
        payload, sig = token.split(".")
        if not hmac.compare_digest(sig, _sig(payload)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
        return data["u"] if data["e"] >= time.time() else None
    except Exception:
        return None


class CurrentUser(dict):
    @property
    def id(self) -> str:
        return self["id"]


def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "authentication required")
    uid = parse_token(authorization.split(" ", 1)[1])
    if not uid:
        raise HTTPException(401, "invalid or expired token")
    row = db.q1("SELECT * FROM users WHERE id=? AND active=1", (uid,))
    if not row:
        raise HTTPException(401, "unknown or disabled user")
    roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (uid,))]
    return CurrentUser(id=row["id"], username=row["username"], display_name=row["display_name"],
                       roles=roles, authz_version=row["authz_version"],
                       capabilities=sorted(authz.capabilities_for_roles(roles)))


def require_capability(cap: str):
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if cap not in user["capabilities"]:
            raise HTTPException(403, f"capability '{cap}' required")
        return user
    return dep
