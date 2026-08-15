from flask import Blueprint, current_app, jsonify, request, session
from ..content import ENEMIES
from ..models import create_run,get_run,save_run,stats,has_contract,map_snapshot
from ..game.combat import armor_damage,q_raw,advance_q,boss_q3_damage
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
        linked=c.execute('SELECT 1 FROM map_edges WHERE run_id=? AND from_node_id=? AND to_node_id=?',(rid,current,node_id)).fetchone()
        if not linked: return jsonify(ok=False,error='node_locked'),409
        c.execute("UPDATE map_nodes SET state='left' WHERE id=?",(current,)); c.execute("UPDATE map_nodes SET state='current' WHERE id=?",(node_id,)); c.execute('UPDATE run_map_state SET current_node_id=? WHERE run_id=?',(node_id,rid))
        kind=c.execute('SELECT node_type FROM map_nodes WHERE id=?',(node_id,)).fetchone()['node_type']
        stage={'normal':'minion','elite':'monster','hero':'hero','shop':'shop','campfire':'campfire','boss':'boss','event':'event'}.get(kind,'event')
        hp=ENEMIES[stage][1] if stage in ENEMIES else 0
        c.execute('UPDATE runs SET stage=?, enemy_hp=? WHERE id=?',(stage,hp,rid))
    return jsonify(ok=True,map=map_snapshot(current_app,rid))
@bp.post("/api/boss/start")
def boss_start():
    rid=session.get("run_id"); run=get_run(current_app,rid) if rid else None
    if not run or run["stage"]!="shop": return jsonify(ok=False,error="stage_locked"),409
    run["stage"]="boss"; run["boss_hp"]=32000; save_run(current_app,run); return jsonify(ok=True,**snapshot(rid))
@bp.post("/api/game/action")
def action():
    rid=session.get("run_id"); run=get_run(current_app,rid) if rid else None; act=(request.get_json(silent=True) or {}).get("action")
    if not run or act not in {"attack","q","e","r"}: return jsonify(ok=False,error="invalid_action"),400
    st=stats(current_app,rid); boss=run["stage"]=="boss"
    if run["stage"] not in {*ENEMIES,"boss"}: return jsonify(ok=False,error="stage_locked"),409
    target_armor=200 if boss else ENEMIES[run["stage"]][3]; target_hp=run["boss_hp"] if boss else run["enemy_hp"]
    attack=st["attack"]*(1.25 if run["ult_turns"] else 1); raw=0
    if act=="attack": raw=attack
    elif act=="q": raw=q_raw(run["q_stage"],attack); stage=run["q_stage"]; run["q_stage"]=advance_q(stage); raw = raw*7.5+32000*.35 if boss and stage==3 and has_contract(current_app,rid) else raw
    elif act=="e": run["e_lifesteal_turns"]=3
    else: run["ult_turns"]=3
    dealt=armor_damage(raw,target_armor); target_hp-=dealt
    if boss and has_contract(current_app,rid) and act=="q" and stage==3 and 0<target_hp<12800: target_hp=0
    if raw and run["e_lifesteal_turns"]: run["hp"]=min(st["max_hp"],run["hp"]+int(dealt*.3)); run["e_lifesteal_turns"]-=1
    if target_hp<=0:
        if boss: run["boss_hp"]=0; run["won"]=1
        else:
            _,_,_,_,reward,nxt=ENEMIES[run["stage"]]; run["gold"]+=reward; run["stage"]=nxt; run["enemy_hp"]=ENEMIES[nxt][1] if nxt in ENEMIES else 0
    else:
        if boss:
            if target_hp<12800: run["boss_awakened"]=1
            enemy_attack=8000 if run["boss_awakened"] else 5000
        else: enemy_attack=ENEMIES[run["stage"]][2]
        run["hp"]-=armor_damage(enemy_attack,st["armor"]+(100 if act=="e" else 0))
        if boss and run["boss_awakened"]: target_hp=min(32000,target_hp+12800)
        if boss: run["boss_hp"]=target_hp
        else: run["enemy_hp"]=target_hp
    if run["ult_turns"]: run["ult_turns"]-=1
    save_run(current_app,run); return jsonify(ok=True,damage=dealt,**snapshot(rid))
