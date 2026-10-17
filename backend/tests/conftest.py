import pytest
from fastapi.testclient import TestClient

from app import db, seed
from app.config import get_settings
from app.services import authz, rag


@pytest.fixture(autouse=True)
def env(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "llm_provider", "extractive")
    monkeypatch.setattr(s, "embedding_provider", "hashing")
    monkeypatch.setattr(s, "cache_enabled", True)
    monkeypatch.setattr(s, "demo_mode", True)
    monkeypatch.setattr(s, "vaultrag_secret", "test-secret")
    db.init_db(":memory:")
    authz.set_available(True)
    authz.state.fail_after_calls = None
    rag.reset_naive_cache()
    yield


@pytest.fixture
def ids():
    return seed.seed_all()


@pytest.fixture
def users(ids):
    out = {}
    for uid, uname, _, _ in seed.USERS:
        roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (uid,))]
        out[uname] = {"id": uid, "username": uname, "roles": roles}
    return out


@pytest.fixture
def client(ids):
    from app.main import app
    return TestClient(app)


def login(client, username):
    r = client.post("/api/auth/login", json={"username": username, "password": seed.DEMO_PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}
