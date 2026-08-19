import uuid, random
from .db import connect
from .content import AUGMENT_STAT_BONUSES, ENEMIES, ITEMS

def create_run(app, seed=None):
    run_id = str(uuid.uuid4())
    seed = seed if seed is not None else random.randrange(2**31)
    from .game.mapgen import generate_map
    nodes,edges=generate_map(seed)
    node_ids={node['id']: f'{run_id}:{node["id"]}' for node in nodes}
    with connect(app) as c:
        c.execute("INSERT INTO runs(id,stage,gold,enemy_hp,seed) VALUES (?,?,?,?,?)", (run_id,"event",0,0,seed))
        c.executemany("INSERT INTO map_nodes(id,run_id,floor,node_type,state) VALUES (?,?,?,?,?)",[(node_ids[n['id']],run_id,n['floor'],n['node_type'],'current' if n['floor']==1 else 'locked') for n in nodes])
        c.executemany("INSERT INTO map_edges(run_id,from_node_id,to_node_id) VALUES (?,?,?)",[(run_id,node_ids[a],node_ids[b]) for a,b in edges])
        c.execute("INSERT INTO run_map_state(run_id,current_node_id) VALUES (?,?)",(run_id,node_ids['n1_0']))
    return run_id

def get_run(app, run_id):
    with connect(app) as c:
        row=c.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone()
    return dict(row) if row else None

def save_run(app, run):
    keys=[k for k in run if k != "id"]
    with connect(app) as c:
        c.execute("UPDATE runs SET " + ",".join(f"{k}=?" for k in keys) + " WHERE id=?", [run[k] for k in keys]+[run["id"]])

def set_stage(app, run_id, stage):
    with connect(app) as c: c.execute("UPDATE runs SET stage=? WHERE id=?",(stage,run_id))
def set_gold(app, run_id, gold):
    with connect(app) as c: c.execute("UPDATE runs SET gold=? WHERE id=?",(gold,run_id))

def grant_health(app, run_id, amount):
    max_hp=stats(app, run_id)['max_hp']
    with connect(app) as c:
        c.execute('UPDATE runs SET hp=MIN(?,hp+?) WHERE id=?',(max_hp,amount,run_id))
    return get_run(app, run_id)

def augment_effects(app, run_id):
    with connect(app) as c:
        ids={row['augment_id'] for row in c.execute('SELECT augment_id FROM run_augments WHERE run_id=?',(run_id,))}
    return {'lifesteal': 25 if 'soul' in ids else 0, 'giant_slayer': 'giant-slayer' in ids, 'dual_wield': 'dual-wield' in ids}

def stats(app, run_id):
    with connect(app) as c:
        rows=c.execute("SELECT item_id FROM inventory WHERE run_id=?",(run_id,)).fetchall()
        shards=c.execute("SELECT stat_key,amount FROM run_stat_shards WHERE run_id=?",(run_id,)).fetchall()
        augments=c.execute("SELECT augment_id FROM run_augments WHERE run_id=?",(run_id,)).fetchall()
    attack, hp, armor, lifesteal = 350,7000,80,0
    ids=[r["item_id"] for r in rows]
    for i in ids:
        _,_,a,h,ar,_,_=ITEMS[i]; attack+=a; hp+=h; armor+=ar
        if ITEMS[i][5] == 'lifesteal_20': lifesteal += 20
    for s in shards:
        if s["stat_key"] == "attack": attack+=s["amount"]
        elif s["stat_key"] == "health": hp+=s["amount"]
        else: armor+=s["amount"]
    for augment in augments:
        bonus=AUGMENT_STAT_BONUSES.get(augment['augment_id'])
        if not bonus: continue
        stat, amount=bonus
        if stat == 'attack': attack += amount
        elif stat == 'health': hp += amount
        else: armor += amount
    if any(augment['augment_id'] == 'soul' for augment in augments): lifesteal += 25
    attack += ids.count("bloodmail") * int(hp*.005)
    return {"attack":attack,"max_hp":hp,"armor":armor,"lifesteal":lifesteal}

def has_contract(app, run_id):
    with connect(app) as c: return bool(c.execute("SELECT 1 FROM run_augments WHERE run_id=? AND augment_id='darkin-contract'",(run_id,)).fetchone())

def map_snapshot(app, run_id):
    with connect(app) as c:
        nodes=[dict(r) for r in c.execute("SELECT id,floor,node_type,state FROM map_nodes WHERE run_id=? ORDER BY floor,id",(run_id,))]
        edges=[dict(r) for r in c.execute("SELECT from_node_id,to_node_id FROM map_edges WHERE run_id=?",(run_id,))]
        current=c.execute("SELECT current_node_id FROM run_map_state WHERE run_id=?",(run_id,)).fetchone()
    return {'nodes':nodes,'edges':edges,'current_node_id':current['current_node_id'] if current else None,'required_route':['hero','shop','campfire','boss']}

def current_map_node(app, run_id):
    with connect(app) as c:
        return c.execute("""SELECT n.* FROM map_nodes n JOIN run_map_state s ON s.run_id=n.run_id
                            WHERE s.run_id=? AND n.id=s.current_node_id""", (run_id,)).fetchone()
