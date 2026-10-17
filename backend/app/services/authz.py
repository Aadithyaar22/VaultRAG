"""Authorization service: the DB is the single source of truth.

Read access to a document = document is active AND user is active AND one of the user's roles is in
document_acl AND the user is not explicitly denied. There is NO administrator bypass. Administrative
*capabilities* (manage documents/roles, review security events) live in a separate table.
Every call fails closed (raises AuthzUnavailable) when the service is flagged unavailable.
"""
from .. import db


class AuthzUnavailable(Exception):
    pass


class _State:
    available = True
    fail_after_calls: int | None = None  # test hook: go down after N more calls
    calls = 0


state = _State()


def set_available(flag: bool) -> None:
    state.available = flag


def _guard() -> None:
    state.calls += 1
    if state.fail_after_calls is not None:
        state.fail_after_calls -= 1
        if state.fail_after_calls < 0:
            state.available = False
    if not state.available:
        raise AuthzUnavailable("authorization service unavailable")


def capabilities_for_roles(roles: list[str]) -> set[str]:
    if not roles:
        return set()
    rows = db.q("SELECT DISTINCT capability FROM role_capabilities WHERE role IN (%s)"
                % ",".join("?" * len(roles)), tuple(roles))
    return {r["capability"] for r in rows}


def user_snapshot(user_id: str) -> dict | None:
    _guard()
    u = db.q1("SELECT id, active, authz_version FROM users WHERE id=?", (user_id,))
    if not u or not u["active"]:
        return None
    roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (user_id,))]
    return {"id": u["id"], "authz_version": u["authz_version"], "roles": roles}


def accessible_docs(user_id: str) -> dict[str, dict]:
    """doc_id -> {version, acl_version} for every document the user may read right now."""
    snap = user_snapshot(user_id)
    if not snap or not snap["roles"]:
        return {}
    marks = ",".join("?" * len(snap["roles"]))
    rows = db.q(
        f"""SELECT d.id, d.version, d.acl_version FROM documents d
            WHERE d.status='active'
              AND EXISTS (SELECT 1 FROM document_acl a WHERE a.doc_id=d.id AND a.role IN ({marks}))
              AND NOT EXISTS (SELECT 1 FROM document_user_deny x WHERE x.doc_id=d.id AND x.user_id=?)""",
        tuple(snap["roles"]) + (user_id,))
    return {r["id"]: {"version": r["version"], "acl_version": r["acl_version"]} for r in rows}


def can_read(user_id: str, doc_id: str) -> bool:
    return doc_id in accessible_docs(user_id)


def all_active_docs() -> dict[str, dict]:
    """Used ONLY by the intentionally insecure 'conventional RAG' baseline."""
    rows = db.q("SELECT id, version, acl_version FROM documents WHERE status='active'")
    return {r["id"]: {"version": r["version"], "acl_version": r["acl_version"]} for r in rows}
