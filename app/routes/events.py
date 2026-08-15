import json
import random
from math import ceil
from flask import Blueprint, current_app, jsonify, request, session
from ..db import connect
from ..models import get_run, stats

bp = Blueprint('events', __name__)
OFFERS = {
    'loot': {'title': '战利品箱', 'choices': [{'key': 'gold', 'text': '获得 900 金币'}, {'key': 'reroll', 'text': '获得 1 张刷新券'}]},
    'altar': {'title': '血契祭坛', 'choices': [{'key': 'attack', 'text': '失去 20% 当前生命，获得 80 攻击'}, {'key': 'armor', 'text': '失去 15% 当前生命，获得 45 护甲'}]},
    'relic': {'title': '暗裔遗物', 'choices': [{'key': 'health', 'text': '获得 1200 最大生命'}, {'key': 'relic_attack', 'text': '获得 50 攻击'}]},
}

def active_event(run_id, node_id):
    with connect() as c:
        return c.execute("""SELECT 1 FROM map_nodes n JOIN run_map_state s ON s.run_id=n.run_id
                            WHERE n.id=? AND n.run_id=? AND n.node_type='event'
                              AND n.state='current' AND s.current_node_id=n.id""", (node_id, run_id)).fetchone()

@bp.get('/api/events/<node_id>')
def event_offer(node_id):
    run_id = session.get('run_id'); run = get_run(current_app, run_id) if run_id else None
    if not run or run['status'] == 'failed' or not active_event(run_id, node_id): return jsonify(ok=False, error='invalid_event'), 409
    with connect() as c:
        row = c.execute('SELECT event_key,offer_json,chosen_key FROM node_events WHERE run_id=? AND node_id=?', (run_id, node_id)).fetchone()
        if not row:
            key = random.choice(list(OFFERS)); offer = {'event_key': key, **OFFERS[key]}
            c.execute('INSERT INTO node_events(run_id,node_id,event_key,offer_json) VALUES (?,?,?,?)', (run_id, node_id, key, json.dumps(offer)))
        else: offer = json.loads(row['offer_json'])
    return jsonify(ok=True, offer=offer)

@bp.post('/api/events/<node_id>/choose')
def choose_event(node_id):
    run_id = session.get('run_id'); run = get_run(current_app, run_id) if run_id else None
    choice = (request.get_json(silent=True) or {}).get('choice_key')
    if not run or run['status'] == 'failed' or not active_event(run_id, node_id): return jsonify(ok=False, error='invalid_event'), 409
    with connect() as c:
        row = c.execute('SELECT offer_json,chosen_key FROM node_events WHERE run_id=? AND node_id=?', (run_id, node_id)).fetchone()
        if not row or row['chosen_key']: return jsonify(ok=False, error='event_resolved'), 409
        offer = json.loads(row['offer_json'])
        if choice not in {item['key'] for item in offer['choices']}: return jsonify(ok=False, error='invalid_choice'), 400
        c.execute('UPDATE node_events SET chosen_key=? WHERE run_id=? AND node_id=? AND chosen_key IS NULL', (choice, run_id, node_id))
        if choice == 'gold': c.execute('UPDATE runs SET gold=gold+900 WHERE id=?', (run_id,)); result = '获得 900 金币。'
        elif choice == 'reroll': c.execute('UPDATE runs SET reroll_tokens=reroll_tokens+1 WHERE id=?', (run_id,)); result = '获得 1 张刷新券。'
        elif choice in {'attack', 'armor'}:
            fraction = .20 if choice == 'attack' else .15; amount = 80 if choice == 'attack' else 45
            c.execute('UPDATE runs SET hp=MAX(1,hp-CEIL(hp*?)) WHERE id=?', (fraction, run_id))
            c.execute('INSERT INTO run_stat_shards(run_id,tier,stat_key,amount) VALUES (?,?,?,?)', (run_id, 'event', choice, amount))
            result = f'血契生效，获得 {amount} {"攻击" if choice == "attack" else "护甲"}。'
        else:
            stat, amount = ('health', 1200) if choice == 'health' else ('attack', 50)
            c.execute('INSERT INTO run_stat_shards(run_id,tier,stat_key,amount) VALUES (?,?,?,?)', (run_id, 'event', stat, amount))
            result = f'遗物赋予 {amount} {"生命" if stat == "health" else "攻击"}。'
        c.execute("UPDATE map_nodes SET state='closed' WHERE id=?", (node_id,))
        c.execute("UPDATE runs SET stage='event' WHERE id=?", (run_id,))
    return jsonify(ok=True, result=result, run=get_run(current_app, run_id), stats=stats(current_app, run_id))
