import time
from flask import Blueprint, current_app, jsonify, session
from ..db import connect
from ..models import get_run
bp = Blueprint("rewards", __name__)

@bp.post("/api/rewards/hero/claim")
def claim():
    rid=session.get("run_id"); run=get_run(current_app,rid) if rid else None
    if not run or run["stage"]!="shop": return jsonify(ok=False,error="stage_locked"),409
    with connect() as c: claimed=c.execute("SELECT 1 FROM reward_claims WHERE run_id=? AND reward_key='hero'",(rid,)).fetchone()
    if claimed: return jsonify(ok=False,error="already_claimed"),409
    time.sleep(current_app.config["RACE_WINDOW_MS"]/1000)
    with connect() as c: c.execute("UPDATE runs SET gold=gold+3000,reroll_tokens=reroll_tokens+1 WHERE id=?",(rid,))
    with connect() as c: c.execute("INSERT OR IGNORE INTO reward_claims(run_id,reward_key) VALUES (?,'hero')",(rid,))
    return jsonify(ok=True,run=get_run(current_app,rid))
