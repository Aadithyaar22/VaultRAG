from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import auth, db
from ..config import get_settings
from ..services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(body: LoginIn):
    row = db.q1("SELECT * FROM users WHERE username=? AND active=1", (body.username,))
    if not row or not auth.verify_password(body.password, row["password_hash"]):
        audit.log("login_failed", outcome="blocked", username_len=len(body.username))
        raise HTTPException(401, "invalid credentials")
    audit.log("login", user_id=row["id"], outcome="ok")
    return {"token": auth.make_token(row["id"])}


@router.get("/me")
def me(user=Depends(auth.current_user)):
    return {k: user[k] for k in ("id", "username", "display_name", "roles", "capabilities")}


@router.get("/demo-users")
def demo_users():
    """Demo-only identity picker (synthetic users). Disabled when DEMO_MODE=false."""
    if not get_settings().demo_mode:
        raise HTTPException(404, "not found")
    out = []
    for u in db.q("SELECT id, username, display_name FROM users ORDER BY username"):
        roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (u["id"],))]
        out.append({**dict(u), "roles": roles})
    return out
