import random
from flask import Blueprint, current_app, jsonify, request, session
from ..content import ENEMIES, enemy_for_floor
from ..models import create_run,get_run,save_run,stats,has_contract,map_snapshot,current_map_node
from ..game.combat import boss_q3_damage, resolve_turn
bp = Blueprint("game", __name__)

def snapshot(rid):
    run=get_run(current_app,rid); out={"run":run,"stats":stats(current_app,rid)}
    if run and run["won"]: out["flag"]=current_app.config["FLAG"]
    return out

@bp.post("/api/runs")
def start():
    rid=create_run(current_app); session["run_id"]=rid; return jsonify(ok=True,**snapshot(rid))
@bp.get("/api/state")
def state():
    rid=session.get("run_id"); return (jsonify(ok=True,**snapshot(rid)) if rid else (jsonify(ok=False,error="run_not_found"),404))
@bp.get('/api/map')
def game_map():
    rid=session.get('run_id')
    return (jsonify(ok=True,map=map_snapshot(current_app,rid)) if rid else (jsonify(ok=False,error='run_not_found'),404))
@bp.post('/api/map/enter/<node_id>')
def enter_node(node_id):
    rid=session.get('run_id'); run=get_run(current_app,rid) if rid else None
    if not run or run.get('status')=='failed': return jsonify(ok=False,error='run_failed'),409
    from ..db import connect
    with connect() as c:
        current=c.execute('SELECT current_node_id FROM run_map_state WHERE run_id=?',(rid,)).fetchone()['current_node_id']
        current_node=c.execute('SELECT node_type,state FROM map_nodes WHERE id=?',(current,)).fetchone()
        if current_node['node_type'] != 'start' and current_node['state'] not in {'cleared', 'closed'}:
            return jsonify(ok=False,error='node_not_cleared'),409
        linked=c.execute('SELECT 1 FROM map_edges WHERE run_id=? AND from_node_id=? AND to_node_id=?',(rid,current,node_id)).fetchone()
        if not linked: return jsonify(ok=False,error='node_locked'),409
        c.execute("UPDATE map_nodes SET state='left' WHERE id=?",(current,)); c.execute("UPDATE map_nodes SET state='current' WHERE id=?",(node_id,)); c.execute('UPDATE run_map_state SET current_node_id=? WHERE run_id=?',(node_id,rid))
        node_row=c.execute('SELECT node_type,floor FROM map_nodes WHERE id=?',(node_id,)).fetchone(); kind=node_row['node_type']
        stage={'normal':'minion','elite':'monster','hero':'hero','shop':'shop','campfire':'campfire','boss':'boss','event':'event'}.get(kind,'event')
        hp=enemy_for_floor(stage, node_row['floor'])['hp'] if stage in ENEMIES else 0
        c.execute('UPDATE runs SET stage=?, enemy_hp=?, enemy_max_hp=? WHERE id=?',(stage,hp,hp,rid))
        if kind == 'shop':
            c.execute("UPDATE map_nodes SET state='cleared' WHERE id=?", (node_id,))
    return jsonify(ok=True, **snapshot(rid), map=map_snapshot(current_app,rid))
@bp.post("/api/game/action")
def action():
    rid=session.get("run_id"); run=get_run(current_app,rid) if rid else None; act=(request.get_json(silent=True) or {}).get("action")
    if not run or act not in {"q","w","e","r"}: return jsonify(ok=False,error="invalid_action"),400
    if run.get('status') == 'failed': return jsonify(ok=False,error='run_failed'),409
    st=stats(current_app,rid); boss=run["stage"]=="boss"
    if run["stage"] not in {*ENEMIES,"boss"}: return jsonify(ok=False,error="stage_locked"),409
    enemy = None if boss else enemy_for_floor(run['stage'], current_map_node(current_app, rid)['floor'])
    target_armor=200 if boss else enemy['armor']; target_hp=run["boss_hp"] if boss else run["enemy_hp"]
    q_stage=run['q_stage']
    state=resolve_turn(run, act, st['attack'], st['armor'], 8000 if boss and run['boss_awakened'] else (5000 if boss else enemy['attack']), target_armor, [random.random(), random.random()], lifesteal=st['lifesteal'], max_hp=st['max_hp'])
    dealt=state['damage']
    if boss and act == 'q' and q_stage == 3 and has_contract(current_app,rid):
        attack=st['attack'] * (1.25 if run['ult_turns'] else 1)
        dealt=boss_q3_damage(attack, target_armor, 32000, True) if state['hit'] else 0
        if state['hit']:
            lifesteal=st['lifesteal'] + (30 if run['e_lifesteal_turns'] else 0)
            healing=min(st['max_hp']-run['hp'], int(dealt*lifesteal/100))
            state['hp'] += healing-state['healing']
            state['healing'] = healing
    target_hp-=dealt
    if boss and has_contract(current_app,rid) and act=="q" and q_stage==3 and 0 < target_hp < 12800: target_hp=0
    for key in ('q_stage','e_lifesteal_turns','ult_turns','w_debuff_pending','hp'):
        if key in state: run[key]=state[key]
    run['hp']=min(st['max_hp'], run['hp'])
    if target_hp<=0:
        if boss: run["boss_hp"]=0; run["won"]=1
        else:
            reward=enemy['reward']; run["gold"]+=reward; run["stage"]='cleared'; run["enemy_hp"]=0
            from ..db import connect
            with connect() as c: c.execute("UPDATE map_nodes SET state='cleared' WHERE id=(SELECT current_node_id FROM run_map_state WHERE run_id=?)",(rid,))
    else:
        if boss and target_hp<12800: run["boss_awakened"]=1
        if boss and run["boss_awakened"]: target_hp=min(32000,target_hp+12800)
        if boss: run["boss_hp"]=target_hp
        else: run["enemy_hp"]=target_hp
        if run['hp'] <= 0: run['hp']=0; run['status']='failed'
    save_run(current_app,run)
    return jsonify(ok=True, damage=dealt, healing=state['healing'], gold_reward=reward if target_hp <= 0 and not boss else 0, hit=state['hit'], enemy_damage=state['enemy_damage'], **snapshot(rid))
