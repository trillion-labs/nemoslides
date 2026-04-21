"""Blindtest voting platform — multi-user.

Run:
    uv run uvicorn blindtest.app:app --host 127.0.0.1 --port 8001

Each annotator picks a handle on first visit (stored in a cookie). Every
annotator independently votes on the full pair queue. Per-pair win rate
is aggregated across all annotators on the /results page.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).resolve().parent
REPO_ROOT = BASE.parent
QUEUE_PATH = BASE / "pair_queue.json"
DB_PATH = BASE / "votes.db"
RUNS_ROOT = REPO_ROOT / "eval" / "runs"

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
COOKIE_NAME = "annotator"
COOKIE_MAX_AGE = 60 * 60 * 24 * 90  # 90 days
N_SHARDS = int(os.environ.get("BLINDTEST_SHARDS", "4"))

app = FastAPI(title="slides-sft blindtest")
templates = Jinja2Templates(directory=str(BASE / "templates"))


# -------- tokens --------

def pair_token(pair_id: str) -> str:
    return hashlib.sha256(pair_id.encode()).hexdigest()[:12]


def flip_for(token: str) -> bool:
    return (int(hashlib.sha256(f"flip:{token}".encode()).hexdigest()[:8], 16) & 1) == 1


# -------- data --------

def load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        raise HTTPException(500, "pair_queue.json missing — run `uv run python -m blindtest.build_pairs` first")
    q = json.loads(QUEUE_PATH.read_text())
    for p in q:
        p["token"] = pair_token(p["pair_id"])
    return q


def indexed_queue() -> tuple[list[dict], dict[str, dict]]:
    q = load_queue()
    return q, {p["token"]: p for p in q}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(votes)")}
    if cols and "annotator_id" not in cols:
        conn.execute("DROP TABLE votes")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            annotator_id  TEXT NOT NULL,
            pair_id       TEXT NOT NULL,
            seed_id       TEXT NOT NULL,
            model_left    TEXT NOT NULL,
            model_right   TEXT NOT NULL,
            winner        TEXT NOT NULL CHECK(winner IN ('left', 'tie', 'right')),
            voted_at      TEXT NOT NULL,
            UNIQUE(annotator_id, pair_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS annotators (
            annotator_id  TEXT PRIMARY KEY,
            shard         INTEGER NOT NULL,
            joined_at     TEXT NOT NULL
        )
    """)
    return conn


def voted_pair_ids_for(annotator: str) -> set[str]:
    with db() as conn:
        return {r[0] for r in conn.execute(
            "SELECT pair_id FROM votes WHERE annotator_id = ?", (annotator,)
        )}


def get_or_assign_shard(annotator: str) -> int:
    """Return the shard for this annotator, assigning one on first sign-in.

    Shard = (existing annotator count) mod N_SHARDS. Round-robin so the
    first N_SHARDS annotators get distinct shards; subsequent annotators
    double-up (providing K>=2 coverage on some shards).
    """
    with db() as conn:
        row = conn.execute(
            "SELECT shard FROM annotators WHERE annotator_id = ?", (annotator,)
        ).fetchone()
        if row:
            return row[0]
        count = conn.execute("SELECT COUNT(*) FROM annotators").fetchone()[0]
        shard = count % N_SHARDS
        conn.execute(
            "INSERT INTO annotators (annotator_id, shard, joined_at) VALUES (?, ?, ?)",
            (annotator, shard, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        return shard


def pairs_in_shard(shard: int) -> list[dict]:
    """Stride-sampled subset of the queue for this shard index."""
    queue = load_queue()
    return [p for i, p in enumerate(queue) if i % N_SHARDS == shard]


def next_pair_for(annotator: str) -> dict | None:
    """Next unvoted pair within this annotator's shard. Deterministic order."""
    shard = get_or_assign_shard(annotator)
    voted_by_me = voted_pair_ids_for(annotator)
    for p in pairs_in_shard(shard):
        if p["pair_id"] not in voted_by_me:
            return p
    return None


def sides_for(pair: dict) -> tuple[str, str]:
    if flip_for(pair["token"]):
        return pair["model_b"], pair["model_a"]
    return pair["model_a"], pair["model_b"]


def slide_count(model: str, seed_id: str) -> int:
    d = RUNS_ROOT / model / seed_id / "slides"
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.png")))


# -------- annotator auth --------

def current_annotator(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE_NAME)
    if raw and NAME_RE.match(raw):
        return raw
    return None


def redirect_to_who() -> RedirectResponse:
    return RedirectResponse("/who", status_code=303)


# -------- routes --------

@app.get("/who", response_class=HTMLResponse)
def who_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(request, "who.html", {
        "error": error,
        "current": current_annotator(request),
    })


@app.post("/who")
def who_submit(name: str = Form(...)):
    name = name.strip()
    if not NAME_RE.match(name):
        return RedirectResponse("/who?error=bad_name", status_code=303)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        COOKIE_NAME, name,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return resp


@app.post("/logout")
def logout():
    resp = RedirectResponse("/who", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/", response_class=HTMLResponse)
def index(annotator: str | None = Depends(current_annotator)):
    if not annotator:
        return redirect_to_who()
    nxt = next_pair_for(annotator)
    if nxt is None:
        return RedirectResponse("/done", status_code=303)
    return RedirectResponse(f"/vote/{nxt['token']}", status_code=303)


@app.get("/done", response_class=HTMLResponse)
def done_page(request: Request, annotator: str | None = Depends(current_annotator)):
    if not annotator:
        return redirect_to_who()
    shard = get_or_assign_shard(annotator)
    shard_pairs = pairs_in_shard(shard)
    shard_pair_ids = {p["pair_id"] for p in shard_pairs}
    voted = voted_pair_ids_for(annotator) & shard_pair_ids
    return templates.TemplateResponse(request, "done.html", {
        "annotator": annotator,
        "done": len(voted),
        "total": len(shard_pairs),
    })


@app.get("/vote/{token}", response_class=HTMLResponse)
def vote_page(request: Request, token: str, annotator: str | None = Depends(current_annotator)):
    if not annotator:
        return redirect_to_who()
    _, by_token = indexed_queue()
    if token not in by_token:
        raise HTTPException(404, "unknown pair")
    pair = by_token[token]

    shard = get_or_assign_shard(annotator)
    shard_pairs = pairs_in_shard(shard)
    shard_pair_ids = {p["pair_id"] for p in shard_pairs}

    # Enforce shard boundary — someone sharing a URL can't vote on another
    # annotator's pair. Silently redirect to their own next pair.
    if pair["pair_id"] not in shard_pair_ids:
        return RedirectResponse("/", status_code=303)

    voted = voted_pair_ids_for(annotator)

    model_left, model_right = sides_for(pair)
    n_left = slide_count(model_left, pair["seed_id"])
    n_right = slide_count(model_right, pair["seed_id"])

    left_urls = [f"/img/{token}/left/{i + 1:02d}.png" for i in range(n_left)]
    right_urls = [f"/img/{token}/right/{i + 1:02d}.png" for i in range(n_right)]

    return templates.TemplateResponse(request, "vote.html", {
        "token": token,
        "annotator": annotator,
        "prompt": pair["prompt"],
        "slides_left": left_urls,
        "slides_right": right_urls,
        "done": len(voted & shard_pair_ids),
        "total": len(shard_pairs),
        "already_voted": pair["pair_id"] in voted,
    })


@app.get("/img/{token}/{side}/{name}")
def serve_img(token: str, side: str, name: str):
    if side not in {"left", "right"}:
        raise HTTPException(404)
    if ".." in name or "/" in name:
        raise HTTPException(400)
    _, by_token = indexed_queue()
    if token not in by_token:
        raise HTTPException(404)
    pair = by_token[token]
    model_left, model_right = sides_for(pair)
    model = model_left if side == "left" else model_right
    path = RUNS_ROOT / model / pair["seed_id"] / "slides" / name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/png")


@app.post("/vote/{token}")
def submit_vote(
    token: str,
    winner: str = Form(...),
    annotator: str | None = Depends(current_annotator),
):
    if not annotator:
        return redirect_to_who()
    if winner not in {"left", "tie", "right"}:
        raise HTTPException(400, f"bad winner: {winner}")
    _, by_token = indexed_queue()
    if token not in by_token:
        raise HTTPException(404, "unknown pair")
    pair = by_token[token]
    shard = get_or_assign_shard(annotator)
    shard_pair_ids = {p["pair_id"] for p in pairs_in_shard(shard)}
    if pair["pair_id"] not in shard_pair_ids:
        return RedirectResponse("/", status_code=303)
    model_left, model_right = sides_for(pair)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db() as conn:
        conn.execute(
            """INSERT INTO votes (annotator_id, pair_id, seed_id, model_left, model_right, winner, voted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(annotator_id, pair_id) DO UPDATE SET
                 model_left=excluded.model_left,
                 model_right=excluded.model_right,
                 winner=excluded.winner,
                 voted_at=excluded.voted_at""",
            (annotator, pair["pair_id"], pair["seed_id"], model_left, model_right, winner, now),
        )
    return RedirectResponse("/", status_code=303)


@app.post("/undo")
def undo_last(annotator: str | None = Depends(current_annotator)):
    if not annotator:
        return redirect_to_who()
    with db() as conn:
        row = conn.execute(
            "SELECT pair_id FROM votes WHERE annotator_id = ? ORDER BY voted_at DESC LIMIT 1",
            (annotator,),
        ).fetchone()
        if not row:
            return RedirectResponse("/", status_code=303)
        conn.execute(
            "DELETE FROM votes WHERE annotator_id = ? AND pair_id = ?",
            (annotator, row[0]),
        )
    return RedirectResponse(f"/vote/{pair_token(row[0])}", status_code=303)


@app.get("/results", response_class=HTMLResponse)
def results(request: Request):
    queue = load_queue()
    models = sorted({p["model_a"] for p in queue} | {p["model_b"] for p in queue})

    with db() as conn:
        rows = conn.execute(
            "SELECT annotator_id, pair_id, seed_id, model_left, model_right, winner, voted_at "
            "FROM votes ORDER BY voted_at"
        ).fetchall()

    # Aggregate across annotators. Each (annotator, pair) row contributes
    # independently — so a pair voted on by 3 annotators contributes 3 counts.
    wins: dict[str, float] = {m: 0.0 for m in models}
    plays: dict[str, int] = {m: 0 for m in models}
    matrix: dict[str, dict[str, float]] = {a: {b: 0.0 for b in models} for a in models}
    pair_counts: dict[str, dict[str, int]] = {a: {b: 0 for b in models} for a in models}
    per_annotator: dict[str, int] = {}

    for ann, _pid, _seed, ml, mr, w, _vat in rows:
        per_annotator[ann] = per_annotator.get(ann, 0) + 1
        plays[ml] += 1
        plays[mr] += 1
        pair_counts[ml][mr] += 1
        pair_counts[mr][ml] += 1
        if w == "left":
            wins[ml] += 1
            matrix[ml][mr] += 1
        elif w == "right":
            wins[mr] += 1
            matrix[mr][ml] += 1
        else:
            wins[ml] += 0.5
            wins[mr] += 0.5
            matrix[ml][mr] += 0.5
            matrix[mr][ml] += 0.5

    win_rate = {m: (wins[m] / plays[m] if plays[m] else 0.0) for m in models}
    leaderboard = sorted(models, key=lambda m: -win_rate[m])

    pair_win_rate: dict[str, dict[str, float | None]] = {}
    for a in models:
        pair_win_rate[a] = {}
        for b in models:
            if a == b or pair_counts[a][b] == 0:
                pair_win_rate[a][b] = None
            else:
                pair_win_rate[a][b] = matrix[a][b] / pair_counts[a][b]

    return templates.TemplateResponse(request, "results.html", {
        "models": models,
        "leaderboard": leaderboard,
        "wins": wins,
        "plays": plays,
        "win_rate": win_rate,
        "pair_win_rate": pair_win_rate,
        "pair_counts": pair_counts,
        "per_annotator": sorted(per_annotator.items(), key=lambda x: -x[1]),
        "total_votes": len(rows),
        "total_pairs": len(queue),
    })


@app.get("/export.csv")
def export_csv():
    with db() as conn:
        rows = conn.execute(
            "SELECT annotator_id, pair_id, seed_id, model_left, model_right, winner, voted_at "
            "FROM votes ORDER BY voted_at"
        ).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["annotator_id", "pair_id", "seed_id", "model_left", "model_right", "winner", "voted_at"])
    w.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="blindtest_votes.csv"'},
    )
