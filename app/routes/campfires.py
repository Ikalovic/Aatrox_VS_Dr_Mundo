import json, random
from flask import Blueprint, current_app, jsonify, request, session
from ..db import connect
from ..models import get_run, stats

bp=Blueprint('campfires',__name__)

def public_offer():
    with connect() as c:
        return [dict(row) for row in c.execute(
            'SELECT id,name,rarity,description FROM augments WHERE hidden=0 ORDER BY RANDOM() LIMIT 3'
        ).fetchall()]

def save_offer(rid, node, offer, refreshed=False):
    session['campfire_node'] = node
    session['campfire_ids'] = [row['id'] for row in offer]
    with connect() as c:
        c.execute(
            'INSERT INTO campfire_offers(run_id,node_id,offer_json,refreshed_count) VALUES (?,?,?,?)',
            (rid, node, json.dumps(offer), int(refreshed)),
        )

def valid(rid,node):
    with connect() as c:
        return c.execute(
            """SELECT 1 FROM map_nodes n
               JOIN run_map_state s ON s.run_id=n.run_id
               WHERE n.id=? AND n.run_id=? AND n.node_type='campfire'
                 AND n.state='current' AND s.current_node_id=n.id""",
            (node, rid),
        ).fetchone()
@bp.post('/api/campfires/<node>/rest')
def rest(node):
    rid=session.get('run_id'); run=get_run(current_app,rid) if rid else None
    if not run or run.get('status') == 'failed' or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c: c.execute("UPDATE runs SET hp=? WHERE id=?",(stats(current_app,rid)['max_hp'],rid)); c.execute("UPDATE map_nodes SET state='closed' WHERE id=?",(node,))
    return jsonify(ok=True,run=get_run(current_app,rid))
@bp.post('/api/campfires/<node>/meditate')
def meditate(node):
    rid=session.get('run_id')
    run=get_run(current_app,rid) if rid else None
    if not run or run.get('status') == 'failed' or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    offer=public_offer()
    save_offer(rid, node, offer)
    return jsonify(ok=True,offer=offer)

@bp.post('/api/campfires/<node>/meditate/reroll')
def reroll(node):
    rid=session.get('run_id'); run=get_run(current_app,rid) if rid else None
    if not run or run.get('status') == 'failed' or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c:
        changed=c.execute('UPDATE runs SET reroll_tokens=reroll_tokens-1 WHERE id=? AND reroll_tokens>0',(rid,)).rowcount
    if not changed: return jsonify(ok=False,error='no_reroll_tokens'),409
    offer=public_offer()
    save_offer(rid, node, offer, refreshed=True)
    return jsonify(ok=True,offer=offer,run=get_run(current_app,rid))
@bp.get('/api/campfires/<node>/meditate/search')
def search(node):
    rid=session.get('run_id'); q=request.args.get('q','')
    run=get_run(current_app,rid) if rid else None
    if not run or run.get('status') == 'failed' or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c: rows=c.execute(f"SELECT id,name,rarity,description FROM augments WHERE hidden=0 AND name LIKE '%{q}%' LIMIT 20").fetchall()
    offer=[dict(r) for r in rows]
    save_offer(rid, node, offer)
    return jsonify(ok=True,results=offer)
@bp.post('/api/campfires/<node>/meditate/choose')
def choose(node):
    rid=session.get('run_id'); aid=(request.get_json(silent=True) or {}).get('augment_id')
    run=get_run(current_app,rid) if rid else None
    if not run or run.get('status') == 'failed' or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    if session.get('campfire_node') != node or aid not in session.get('campfire_ids',[]): return jsonify(ok=False,error='invalid_id'),400
    with connect() as c: c.execute('INSERT OR IGNORE INTO run_augments(run_id,augment_id) VALUES (?,?)',(rid,aid)); c.execute("UPDATE map_nodes SET state='closed' WHERE id=?",(node,))
    return jsonify(ok=True,augment_id=aid)
