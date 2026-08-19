import random
from flask import Blueprint, current_app, jsonify, request, session
from ..content import ANVIL, ITEMS
from ..db import connect
from ..models import get_run, grant_health, stats
bp = Blueprint("shop", __name__)

def err(code, status=409): return jsonify(ok=False, error=code, message=code), status
def run_id(): return session.get("run_id")

@bp.post("/api/shop/batch-buy")
def batch_buy():
    rid=run_id(); body=request.get_json(silent=True) or {}; ids=body.get("item_ids", [])
    run=get_run(current_app, rid) if rid else None
    if not run or run["stage"] != "shop": return err("stage_locked")
    if not isinstance(ids,list) or not ids or any(i not in ITEMS for i in ids): return err("invalid_id",400)
    unique=list(dict.fromkeys(ids)); cost=sum(ITEMS[i][1] for i in unique)
    if len(unique)>6 or run["gold"]<cost: return err("invalid_purchase")
    with connect() as c:
        for item in ids: c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)",(rid,item))
        c.execute("UPDATE runs SET gold=gold-? WHERE id=?",(cost,rid))
    health_gain=sum(ITEMS[item][3] for item in ids)
    if health_gain: grant_health(current_app,rid,health_gain)
    return jsonify(ok=True, run=get_run(current_app,rid), stats=stats(current_app,rid))

@bp.post("/api/shop/buy")
def buy():
    rid=run_id(); item=(request.get_json(silent=True) or {}).get("item_id")
    run=get_run(current_app,rid) if rid else None
    if not run or run["stage"]!="shop": return err("stage_locked")
    if item not in ITEMS: return err("invalid_id",400)
    with connect() as c:
        owned=[r[0] for r in c.execute("SELECT item_id FROM inventory WHERE run_id=?",(rid,))]
        if len(owned)>=6 or any(ITEMS[x][6]==ITEMS[item][6] for x in owned) or run["gold"]<ITEMS[item][1]: return err("invalid_purchase")
        c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)",(rid,item)); c.execute("UPDATE runs SET gold=gold-? WHERE id=?",(ITEMS[item][1],rid))
    if ITEMS[item][3]: grant_health(current_app,rid,ITEMS[item][3])
    return jsonify(ok=True,run=get_run(current_app,rid),stats=stats(current_app,rid))

def roll_tier():
    r=random.randrange(100); return "silver" if r<80 else "gold" if r<99 else "prismatic"

@bp.post("/api/shop/anvils")
def anvil():
    rid=run_id(); run=get_run(current_app,rid) if rid else None
    if not run or run["stage"]!="shop": return err("stage_locked")
    with connect() as c:
        pending=c.execute("SELECT id,tier FROM stat_anvil_offers WHERE run_id=? AND chosen=0",(rid,)).fetchone()
        if pending: return err("pending_anvil_offer")
        free=c.execute('UPDATE runs SET free_anvils=free_anvils-1 WHERE id=? AND free_anvils>0',(rid,)).rowcount
        if not free:
            used=c.execute("SELECT count(*) FROM run_stat_shards WHERE run_id=? AND tier IN ('silver','gold','prismatic')",(rid,)).fetchone()[0]
            if used>=3: return err("anvil_limit_reached")
            if run["gold"]<750: return err("insufficient_resource")
            c.execute("UPDATE runs SET gold=gold-750 WHERE id=?",(rid,))
        tier=roll_tier(); c.execute("INSERT INTO stat_anvil_offers(run_id,tier) VALUES (?,?)",(rid,tier))
    return jsonify(ok=True,offer={"tier":tier,"options":ANVIL[tier][1]},run=get_run(current_app,rid))

@bp.post("/api/shop/anvils/choose")
def choose_anvil():
    rid=run_id(); key=(request.get_json(silent=True) or {}).get("stat_key")
    with connect() as c:
        offer=c.execute("SELECT id,tier FROM stat_anvil_offers WHERE run_id=? AND chosen=0",(rid,)).fetchone()
        if not offer or key not in ANVIL[offer["tier"]][1]: return err("invalid_id",400)
        c.execute("UPDATE stat_anvil_offers SET chosen=1 WHERE id=?",(offer["id"],)); c.execute("INSERT INTO run_stat_shards(run_id,tier,stat_key,amount) VALUES (?,?,?,?)",(rid,offer["tier"],key,ANVIL[offer["tier"]][1][key]))
    if key == 'health': grant_health(current_app,rid,ANVIL[offer['tier']][1][key])
    return jsonify(ok=True,run=get_run(current_app,rid),stats=stats(current_app,rid))
