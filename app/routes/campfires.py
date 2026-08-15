import json, random
from flask import Blueprint, current_app, jsonify, request, session
from ..db import connect
from ..models import get_run, stats

bp=Blueprint('campfires',__name__)
def valid(rid,node):
    with connect() as c: return c.execute("SELECT 1 FROM map_nodes WHERE id=? AND run_id=? AND node_type='campfire' AND state!='closed'",(node,rid)).fetchone()
@bp.post('/api/campfires/<node>/rest')
def rest(node):
    rid=session.get('run_id'); run=get_run(current_app,rid) if rid else None
    if not run or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c: c.execute("UPDATE runs SET hp=? WHERE id=?",(stats(current_app,rid)['max_hp'],rid)); c.execute("UPDATE map_nodes SET state='closed' WHERE id=?",(node,))
    return jsonify(ok=True,run=get_run(current_app,rid))
@bp.post('/api/campfires/<node>/meditate')
def meditate(node):
    rid=session.get('run_id')
    if not rid or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c:
        rows=c.execute('SELECT id,name,rarity,description FROM augments WHERE hidden=0 ORDER BY RANDOM() LIMIT 3').fetchall(); offer=[dict(r) for r in rows]
        c.execute('INSERT INTO campfire_offers(run_id,node_id,offer_json) VALUES (?,?,?)',(rid,node,json.dumps(offer)))
    return jsonify(ok=True,offer=offer)
@bp.get('/api/campfires/<node>/meditate/search')
def search(node):
    rid=session.get('run_id'); q=request.args.get('q','')
    if not rid or not valid(rid,node): return jsonify(ok=False,error='invalid_campfire'),409
    with connect() as c: rows=c.execute(f"SELECT id,name,rarity,description FROM augments WHERE hidden=0 AND name LIKE '%{q}%' LIMIT 20").fetchall()
    offer=[dict(r) for r in rows]; session['campfire_ids']= [r['id'] for r in offer]
    return jsonify(ok=True,results=offer)
@bp.post('/api/campfires/<node>/meditate/choose')
def choose(node):
    rid=session.get('run_id'); aid=(request.get_json(silent=True) or {}).get('augment_id')
    if not rid or aid not in session.get('campfire_ids',[]): return jsonify(ok=False,error='invalid_id'),400
    with connect() as c: c.execute('INSERT OR IGNORE INTO run_augments(run_id,augment_id) VALUES (?,?)',(rid,aid)); c.execute("UPDATE map_nodes SET state='closed' WHERE id=?",(node,))
    return jsonify(ok=True,augment_id=aid)
