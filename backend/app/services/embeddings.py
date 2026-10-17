"""Embedding providers. 'hashing' is dependency-free and deterministic (portable to s390x with no
native wheels); 'openai_compatible' calls an /embeddings endpoint. Vectors are sparse {dim: weight}."""
import math
import re
import zlib

import httpx

from ..config import get_settings

DIM = 4096
_STOP = set("a an the of to in on for and or is are was were be been it its this that with as at by from "
            "what who how do does can i my me we our you your they their there which will would should "
            "about into than then so if not no".split())


def _tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _hash_embed(text: str) -> dict[int, float]:
    toks = _tokens(text)
    feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    vec: dict[int, float] = {}
    for f in feats:
        i = zlib.crc32(f.encode()) % DIM
        vec[i] = vec.get(i, 0.0) + (1.0 + math.log(1 + f.count("_")))
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {i: v / norm for i, v in vec.items()}


def _api_embed(texts: list[str]) -> list[dict[int, float]]:
    s = get_settings()
    r = httpx.post(s.embedding_base_url.rstrip("/") + "/embeddings",
                   headers={"Authorization": f"Bearer {s.embedding_api_key}"},
                   json={"model": s.embedding_model, "input": texts}, timeout=30)
    r.raise_for_status()
    out = []
    for item in r.json()["data"]:
        v = item["embedding"]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append({i: x / norm for i, x in enumerate(v) if x})
    return out


def embed(texts: list[str]) -> list[dict[int, float]]:
    if get_settings().embedding_provider == "openai_compatible":
        return _api_embed(texts)
    return [_hash_embed(t) for t in texts]


def cosine(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(i, 0.0) for i, v in a.items())
