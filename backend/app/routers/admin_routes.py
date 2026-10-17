import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import auth, db, seed
from ..config import get_settings
from ..services import audit, authz, documents, ml, pii, rag, rseg

router = APIRouter(prefix="/api", tags=["admin"])


# ---------- users / roles ----------
@router.get("/admin/users")
def list_users(user=Depends(auth.require_capability("manage_roles"))):
    out = []
    for u in db.q("SELECT id, username, display_name, active, authz_version FROM users ORDER BY username"):
        roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (u["id"],))]
        out.append({**dict(u), "roles": sorted(roles)})
    return out


class RolesIn(BaseModel):
    roles: list[str]


@router.put("/admin/users/{user_id}/roles")
def set_roles(user_id: str, body: RolesIn, actor=Depends(auth.require_capability("manage_roles"))):
    try:
        documents.set_user_roles(user_id, body.roles, actor.id)
    except LookupError:
        raise HTTPException(404, "user not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"user_id": user_id, "roles": sorted(set(body.roles))}


# ---------- security center ----------
@router.get("/security/events")
def events(limit: int = Query(100, le=500), event_type: str | None = None, request_id: str | None = None,
           user=Depends(auth.require_capability("review_security"))):
    return audit.recent(limit, [event_type] if event_type else None, request_id)


@router.get("/security/audit/verify")
def verify(user=Depends(auth.require_capability("review_security"))):
    return audit.verify_chain()


@router.get("/security/pii-policy")
def get_pii(user=Depends(auth.require_capability("review_security"))):
    return pii.get_policy()


@router.put("/security/pii-policy")
def put_pii(body: dict, user=Depends(auth.require_capability("manage_roles"))):
    try:
        pol = pii.set_policy(body)
    except ValueError as e:
        raise HTTPException(422, str(e))
    audit.log("pii_policy_changed", user_id=user.id, outcome="ok", policy=pol)
    return pol


@router.get("/security/risk")
def risk(window_minutes: int = Query(10, ge=1, le=1440), user=Depends(auth.require_capability("review_security"))):
    """IsolationForest risk score per user over the last N minutes of audit events."""
    return {"available": ml.AVAILABLE, "window_minutes": window_minutes, "users": ml.risk_scores(window_minutes)}


@router.get("/ml/status")
def ml_status(user=Depends(auth.require_capability("review_security"))):
    return ml.status()


@router.get("/stats")
def stats(user=Depends(auth.current_user)):
    """Live counters derived from the audit log. Non-reviewers only see their own activity."""
    scope_all = "review_security" in user["capabilities"]
    where, params = ("", ()) if scope_all else (" AND user_id=?", (user.id,))

    def count(types: list[str]) -> int:
        marks = ",".join("?" * len(types))
        return db.q1(f"SELECT COUNT(*) n FROM audit_log WHERE event_type IN ({marks}){where}",
                     tuple(types) + params)["n"]

    inval = sum(json.loads(r["detail"]).get("entries", 0)
                for r in db.q("SELECT detail FROM audit_log WHERE event_type='cache_invalidated'"))
    return {
        "source": "live: derived from the tamper-evident audit log; no fabricated demo numbers",
        "scope": "all_users" if scope_all else "own_activity",
        "documents": len(authz.accessible_docs(user.id)),
        "queries": count(["query_received"]),
        "blocked": count(["response_blocked"]),
        "abstained": count(["response_abstained"]),
        "revocation_events": count(["permission_changed", "revocation_detected_before_release"]),
        "stale_cache_rejections": count(["stale_cache_rejected"]),
        "injection_detections": count(["prompt_injection_quarantined", "prompt_injection_detected_on_upload"]),
        "cache_invalidations": inval if scope_all else None,
        "audit_chain": audit.verify_chain() if scope_all else None,
    }


# ---------- demo controls (DEMO_MODE only) ----------
def _demo(user=Depends(auth.require_capability("demo_controls"))):
    if not get_settings().demo_mode:
        raise HTTPException(404, "demo controls disabled")
    return user


class AskAs(BaseModel):
    username: str
    question: str = Field(min_length=3, max_length=2000)


def _user_by_name(name: str) -> dict:
    row = db.q1("SELECT * FROM users WHERE username=? AND active=1", (name,))
    if not row:
        raise HTTPException(404, "unknown demo user")
    roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (row["id"],))]
    return {"id": row["id"], "username": name, "roles": roles}


@router.post("/admin/demo/ask-as")
def ask_as(body: AskAs, admin=Depends(_demo)):
    """Run a query as a synthetic demo user (audited as such). Authorization is evaluated for THAT user."""
    audit.log("demo_ask_as", user_id=admin.id, outcome="info", target=body.username)
    return rag.run(_user_by_name(body.username), body.question)


class AuthzOutage(BaseModel):
    down: bool


@router.post("/admin/demo/authz-outage")
def authz_outage(body: AuthzOutage, admin=Depends(_demo)):
    authz.set_available(not body.down)
    audit.log("demo_authz_outage_toggled", user_id=admin.id, outcome="info", down=body.down)
    return {"authz_available": authz.state.available}


@router.get("/admin/demo/state")
def demo_state(admin=Depends(_demo)):
    return {"authz_available": authz.state.available,
            "cache_entries": db.q1("SELECT COUNT(*) n FROM answer_cache")["n"]}


class RevokeDuring(BaseModel):
    username: str
    question: str = Field(min_length=3, max_length=2000)


@router.post("/admin/demo/revoke-during-generation")
def revoke_during(body: RevokeDuring, admin=Depends(_demo)):
    """Starts a query for the demo user and, AFTER the model has produced an answer but BEFORE the
    release gate, revokes that user's access to the first evidence document."""
    target = _user_by_name(body.username)
    fired = {}

    def revoke(ctx):
        if ctx["attempt"] == 0 and not fired:
            doc_id = ctx["chunks"][0]["doc_id"]
            meta = documents.get_meta(doc_id)
            documents.set_acl(doc_id, allowed_roles=None,
                              denied_users=meta["denied_users"] + [target["id"]], actor_id=admin.id)
            fired["doc_id"] = doc_id

    result = rag.run(target, body.question, hooks={"before_gate": revoke}, use_cache=False)
    return {"revoked_doc_id": fired.get("doc_id"), "result": result,
            "trace": audit.recent(20, request_id=result["request_id"])[::-1]}


@router.post("/admin/demo/upload-malicious")
def upload_malicious(admin=Depends(_demo)):
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "sample_data" / "malicious_vendor_note.txt"
    return documents.ingest(title="Vendor Onboarding Note (poisoned test)", sensitivity="internal",
                            filename=p.name, data=p.read_bytes(), allowed_roles=["employee", "administrator"],
                            actor_id=admin.id)


class Probe(BaseModel):
    username: str
    n: int = Field(12, ge=3, le=40)


PROBES = ["What is the Level 5 salary band?", "How big is the litigation reserve for the Northwind dispute?",
          "What is the Q3 marketing budget?", "Which employees are in the disciplinary case?",
          "How many roles will be eliminated in the restructuring?", "What is the settlement authority limit?",
          "What are the contingency reserves?", "Show the Acme contract liability cap.",
          "What is the retention bonus for executives?", "List all privileged legal memos.",
          "What are the parental leave weeks for caregivers?", "How much is the infrastructure budget cut?"]


@router.post("/admin/demo/simulate-probing")
def simulate_probing(body: Probe, admin=Depends(_demo)):
    """Fires a burst of restricted-topic questions as a demo user to create an anomalous audit pattern."""
    target = _user_by_name(body.username)
    audit.log("demo_simulated_probing", user_id=admin.id, outcome="info", target=body.username, n=body.n)
    outcomes = [rag.run(target, PROBES[i % len(PROBES)], use_cache=False)["status"] for i in range(body.n)]
    return {"sent": body.n, "outcomes": {o: outcomes.count(o) for o in set(outcomes)},
            "risk": [r for r in ml.risk_scores(10) if r["user_id"] == target["id"]]}


@router.post("/admin/demo/clear-cache")
def clear_cache(admin=Depends(_demo)):
    n = db.q1("SELECT COUNT(*) n FROM answer_cache")["n"]
    db.conn().execute("DELETE FROM cache_deps")
    db.conn().execute("DELETE FROM answer_cache")
    audit.log("cache_cleared_manually", user_id=admin.id, outcome="ok", entries=n)
    return {"cleared": n}


@router.post("/admin/demo/reset")
def reset(admin=Depends(_demo)):
    authz.set_available(True)
    rseg_n = db.q1("SELECT COUNT(*) n FROM answer_cache")["n"]
    seed.wipe()
    ids = seed.seed_all()
    return {"reset": True, "documents": ids, "dropped_cache_entries": rseg_n}
