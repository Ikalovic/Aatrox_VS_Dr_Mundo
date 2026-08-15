import uuid
from .db import connect
from .content import ENEMIES, ITEMS

def create_run(app):
    run_id = str(uuid.uuid4())
    with connect(app) as c:
        c.execute("INSERT INTO runs(id,stage,gold,enemy_hp) VALUES (?,?,?,?)", (run_id,"minion",0,ENEMIES["minion"][1]))
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

def stats(app, run_id):
    with connect(app) as c:
        rows=c.execute("SELECT item_id FROM inventory WHERE run_id=?",(run_id,)).fetchall()
        shards=c.execute("SELECT stat_key,amount FROM run_stat_shards WHERE run_id=?",(run_id,)).fetchall()
    attack, hp, armor = 350,7000,80
    ids=[r["item_id"] for r in rows]
    for i in ids:
        _,_,a,h,ar,_,_=ITEMS[i]; attack+=a; hp+=h; armor+=ar
    for s in shards:
        if s["stat_key"] == "attack": attack+=s["amount"]
        elif s["stat_key"] == "health": hp+=s["amount"]
        else: armor+=s["amount"]
    attack += ids.count("bloodmail") * int(hp*.005)
    return {"attack":attack,"max_hp":hp,"armor":armor}

def has_contract(app, run_id):
    with connect(app) as c: return bool(c.execute("SELECT 1 FROM run_augments WHERE run_id=? AND augment_id='darkin-contract'",(run_id,)).fetchone())
