import sqlite3
from pathlib import Path
from flask import current_app
from .content import ITEMS, AUGMENTS

SCHEMA = '''
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, stage TEXT NOT NULL, gold INTEGER NOT NULL DEFAULT 0, reroll_tokens INTEGER NOT NULL DEFAULT 1, hp INTEGER NOT NULL DEFAULT 7000, enemy_hp INTEGER NOT NULL DEFAULT 250, enemy_max_hp INTEGER NOT NULL DEFAULT 0, q_stage INTEGER NOT NULL DEFAULT 1, e_lifesteal_turns INTEGER NOT NULL DEFAULT 0, ult_turns INTEGER NOT NULL DEFAULT 0, w_debuff_pending INTEGER NOT NULL DEFAULT 0, boss_hp INTEGER NOT NULL DEFAULT 32000, boss_awakened INTEGER NOT NULL DEFAULT 0, won INTEGER NOT NULL DEFAULT 0, seed INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active');
CREATE TABLE IF NOT EXISTS augments (id TEXT PRIMARY KEY, name TEXT, rarity TEXT, description TEXT, hidden INTEGER, weight INTEGER, effect_key TEXT);
CREATE TABLE IF NOT EXISTS run_augments (run_id TEXT, augment_id TEXT, UNIQUE(run_id, augment_id));
CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, name TEXT, price INTEGER, attack INTEGER, health INTEGER, armor INTEGER, effect_key TEXT, unique_group TEXT);
CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, item_id TEXT);
CREATE TABLE IF NOT EXISTS reward_claims (run_id TEXT, reward_key TEXT, claimed_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(run_id,reward_key));
CREATE TABLE IF NOT EXISTS stat_anvil_offers (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, tier TEXT, chosen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS run_stat_shards (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, tier TEXT, stat_key TEXT, amount INTEGER);
CREATE TABLE IF NOT EXISTS map_nodes (id TEXT PRIMARY KEY, run_id TEXT, floor INTEGER, node_type TEXT, state TEXT DEFAULT 'locked');
CREATE TABLE IF NOT EXISTS map_edges (run_id TEXT, from_node_id TEXT, to_node_id TEXT);
CREATE TABLE IF NOT EXISTS run_map_state (run_id TEXT PRIMARY KEY, current_node_id TEXT, status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS campfire_offers (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, node_id TEXT, offer_json TEXT, chosen INTEGER DEFAULT 0, refreshed_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS node_events (run_id TEXT NOT NULL, node_id TEXT NOT NULL, event_key TEXT NOT NULL, offer_json TEXT NOT NULL, chosen_key TEXT, PRIMARY KEY (run_id,node_id));
'''

def connect(app=None):
    app = app or current_app
    conn = sqlite3.connect(app.config["DATABASE"], timeout=3, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=3000")
    return conn

def init_db(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with connect(app) as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR IGNORE INTO augments VALUES (?,?,?,?,?,?,?)", AUGMENTS)
        conn.executemany("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,?,?,?)", [(k, *v) for k,v in ITEMS.items()])
