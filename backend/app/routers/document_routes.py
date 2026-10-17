from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .. import auth, db
from ..services import authz, documents
from ..services.extract import UnsupportedFile

router = APIRouter(prefix="/api/documents", tags=["documents"])
MAX_BYTES = 10 * 1024 * 1024


def _public(meta: dict, full: bool) -> dict:
    keys = ["id", "title", "sensitivity", "version", "updated_at", "injection_flagged", "pii_count"]
    out = {k: meta[k] for k in keys}
    if full:  # management view: ACLs + versions
        out.update(allowed_roles=meta["allowed_roles"], denied_users=meta["denied_users"],
                   acl_version=meta["acl_version"], versions=meta["versions"], filename=meta["filename"])
    return out


@router.get("")
def list_documents(user=Depends(auth.current_user)):
    """Readable documents only. Managers additionally see management metadata (titles, ACLs, versions)
    for every active document -- never chunk text -- because they cannot administer what they cannot see."""
    manage = "manage_documents" in user["capabilities"]
    readable = authz.accessible_docs(user.id)
    rows = db.q("SELECT id FROM documents WHERE status='active' ORDER BY title")
    out = []
    for r in rows:
        if manage or r["id"] in readable:
            m = documents.get_meta(r["id"])
            d = _public(m, manage)
            d["can_read"] = r["id"] in readable
            out.append(d)
    return out


def _parse_roles(raw: str) -> list[str]:
    return [r.strip() for r in raw.split(",") if r.strip()]


@router.post("")
async def upload(file: UploadFile = File(...), title: str = Form(...), sensitivity: str = Form("internal"),
                 allowed_roles: str = Form(...), user=Depends(auth.require_capability("manage_documents"))):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "file too large (10 MB max)")
    try:
        return documents.ingest(title=title, sensitivity=sensitivity, filename=file.filename or "upload.txt",
                                data=data, allowed_roles=_parse_roles(allowed_roles), actor_id=user.id)
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/{doc_id}/replace")
async def replace(doc_id: str, file: UploadFile = File(...), title: str = Form(...),
                  sensitivity: str = Form("internal"), allowed_roles: str = Form(...),
                  user=Depends(auth.require_capability("manage_documents"))):
    try:
        return documents.ingest(title=title, sensitivity=sensitivity, filename=file.filename or "upload.txt",
                                data=await file.read(), allowed_roles=_parse_roles(allowed_roles),
                                actor_id=user.id, doc_id=doc_id)
    except LookupError:
        raise HTTPException(404, "document not found")
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


class AclIn(BaseModel):
    allowed_roles: list[str] | None = None
    denied_users: list[str] | None = None


@router.put("/{doc_id}/acl")
def update_acl(doc_id: str, body: AclIn, user=Depends(auth.require_capability("manage_documents"))):
    try:
        return documents.set_acl(doc_id, allowed_roles=body.allowed_roles, denied_users=body.denied_users,
                                 actor_id=user.id)
    except LookupError:
        raise HTTPException(404, "document not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{doc_id}")
def delete(doc_id: str, user=Depends(auth.require_capability("manage_documents"))):
    try:
        documents.remove(doc_id, user.id)
    except LookupError:
        raise HTTPException(404, "document not found")
    return {"removed": doc_id}


@router.get("/{doc_id}/passage/{chunk_id}")
def passage(doc_id: str, chunk_id: str, user=Depends(auth.current_user)):
    """Cited-passage lookup. Unreadable and nonexistent documents are indistinguishable (404)."""
    if not authz.can_read(user.id, doc_id):
        raise HTTPException(404, "not found")
    row = db.q1("SELECT c.text, c.doc_version FROM chunks c JOIN documents d ON d.id=c.doc_id AND d.version=c.doc_version "
                "WHERE c.id=? AND c.doc_id=?", (chunk_id, doc_id))
    if not row:
        raise HTTPException(404, "not found")
    from ..services import pii
    return {"text": pii.apply_policy(row["text"], user["roles"])[0], "doc_version": row["doc_version"]}
