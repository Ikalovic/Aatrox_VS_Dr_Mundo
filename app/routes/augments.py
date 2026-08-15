from flask import Blueprint, current_app, jsonify, request, session
from ..db import connect
bp = Blueprint("augments", __name__)

@bp.get("/api/augments/search")
def search():
    q=request.args.get("q","")
    with connect() as c:
        rows=c.execute(f"SELECT id,name,rarity,description FROM augments WHERE hidden=0 AND name LIKE '%{q}%' LIMIT 20").fetchall()
    out=[dict(r) for r in rows]; session["visible_augment_ids"]=[r["id"] for r in out]
    return jsonify(ok=True,results=out)

@bp.post("/api/augments/choose")
def choose():
    rid=session.get("run_id"); aid=(request.get_json(silent=True) or {}).get("augment_id")
    if not rid or aid not in session.get("visible_augment_ids",[]): return jsonify(ok=False,error="invalid_id"),400
    with connect() as c:
        if c.execute("SELECT count(*) FROM run_augments WHERE run_id=?",(rid,)).fetchone()[0]>=3: return jsonify(ok=False,error="augment_limit"),409
        c.execute("INSERT OR IGNORE INTO run_augments(run_id,augment_id) VALUES (?,?)",(rid,aid))
    return jsonify(ok=True,augment_id=aid)
