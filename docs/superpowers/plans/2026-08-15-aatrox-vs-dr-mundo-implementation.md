# Aatrox VS Dr. Mundo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerized Flask CTF game in which the intended SQL injection → reward race → batch-purchase logic-bug chain lets Aatrox defeat Dr. Mundo and reveal the environment-provided Flag.

**Architecture:** Flask blueprints expose a JSON-first game API backed by one SQLite database per container. `combat.py` is a pure state transition module, while routes persist its results; SQLi, the race, and duplicate inventory writes are deliberately isolated to their intended endpoints. The browser is a thin dark-card UI over these APIs.

**Tech Stack:** Python 3.12, Flask, SQLite, pytest, standard-library threading, vanilla HTML/CSS/JavaScript, Docker Compose.

---

## File map

- `app/__init__.py` — application factory and error JSON.
- `app/db.py` — SQLite connection, initialization, transaction helpers.
- `app/content.py` — fixed enemies, items, augments, shard tiers.
- `app/models.py` — run persistence and stat aggregation.
- `app/game/combat.py` — Q cycle, E/R effects, damage, boss resolution.
- `app/routes/game.py` — run creation, map, normal/Boss combat and status.
- `app/routes/augments.py` — random offerings, vulnerable search and choice.
- `app/routes/rewards.py` — intentionally racy hero-reward claim.
- `app/routes/shop.py` — normal purchase, intentionally flawed batch purchase, anvils.
- `app/schema.sql` — tables, indexes and constraints.
- `app/templates/index.html`, `app/static/app.js`, `app/static/style.css` — no-art UI.
- `tests/` — unit, route, race and end-to-end exploit coverage.
- `scripts/solve.py` — organizer-only proof-of-solve script.
- `Dockerfile`, `docker-compose.yml`, `README.md` — deployment and handoff.

### Task 1: Bootstrap the application and health check

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `app/__init__.py`, `app/routes/__init__.py`, `tests/conftest.py`, `tests/test_app.py`

- [ ] **Step 1: Write the failing health-check test**

```python
# tests/test_app.py
def test_health_returns_json(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
```

- [ ] **Step 2: Verify it fails because the app package is absent**

Run: `pytest tests/test_app.py -q`

Expected: collection failure mentioning `app`.

- [ ] **Step 3: Implement the minimal factory**

```python
# requirements.txt
Flask>=3.1,<4
pytest>=8,<9
requests>=2.31,<3

# pytest.ini
[pytest]
testpaths = tests

# app/__init__.py
from flask import Flask, jsonify

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY="dev-secret", DATABASE="game.db", FLAG="flag{development_only}")
    if test_config:
        app.config.update(test_config)

    @app.get("/health")
    def health():
        return jsonify(ok=True)

    return app
```

```python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "game.db"), "FLAG": "flag{test}"})

@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 4: Verify the test passes**

Run: `pytest tests/test_app.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit**

Run: `git add requirements.txt pytest.ini app tests && git commit -m "feat: bootstrap Flask application"`

### Task 2: Create SQLite schema, seed content, and run creation

**Files:**
- Create: `app/db.py`, `app/content.py`, `app/models.py`, `app/schema.sql`, `tests/test_models.py`
- Modify: `app/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Write failing database tests**

```python
from app.models import create_run, get_run

def test_new_run_has_zero_gold_and_minion_stage(app):
    run_id = create_run(app)
    run = get_run(app, run_id)
    assert run["gold"] == 0
    assert run["stage"] == "minion"
    assert run["q_stage"] == 1

def test_seed_contains_hidden_darkin_contract(app):
    from app.db import connect
    with connect(app) as conn:
        row = conn.execute("SELECT hidden, weight FROM augments WHERE id = 'darkin-contract'").fetchone()
    assert tuple(row) == (1, 1)
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_models.py -q`

Expected: import failure for `app.models`.

- [ ] **Step 3: Implement schema and deterministic seed data**

Create `runs`, `augments`, `run_augments`, `items`, `inventory`, `stat_anvil_offers`, `run_stat_shards`, `reward_claims`, and `battle_log` exactly as named in the design. `runs` contains `stage`, `gold`, `reroll_tokens`, `hp`, `max_hp`, `enemy_hp`, `q_stage`, `e_lifesteal_turns`, `ult_turns`, `boss_hp`, `boss_awakened`, and `won`.

Use these required content records:

```python
# app/content.py
AUGMENTS = [
    ("darkin-contract", "暗裔契约", "prismatic", "Q3 获得最大生命伤害与斩杀", 1, 1, "darkin_contract"),
    ("gamba", "掷骰狂人", "prismatic", "刷新券+2", 0, 120_000_000, "reroll"),
    ("soul", "吞噬灵魂", "gold", "最大生命+800", 0, 120_000_000, "health"),
    ("dragon", "全能龙魂", "prismatic", "攻击+60", 0, 120_000_000, "attack"),
    ("goliath", "歌利亚巨人", "prismatic", "最大生命+1200", 0, 120_000_000, "health"),
    ("ika", "艾卡西亚的陷落", "prismatic", "护甲+35", 0, 120_000_000, "armor"),
    ("basics", "回归基本功", "gold", "攻击+30", 0, 100_000_000, "attack"),
    ("slap", "扇巴掌", "silver", "攻击+15", 0, 100_000_000, "attack"),
    ("tooth", "牙仙子", "silver", "最大生命+600", 0, 100_000_000, "health"),
    ("escape", "逃跑计划", "silver", "护甲+10", 0, 99_999_999, "armor"),
]
ITEMS = [
    ("heartsteel", "心之钢", 3300, 40, 3000, 0, "none", "core-health"),
    ("bloodmail", "霸王血铠", 3200, 100, 2500, 0, "bloodmail", "core-bloodmail"),
    ("bloodthirster", "饮血剑", 3400, 90, 0, 0, "lifesteal_20", "bloodthirster"),
]
ENEMIES = {
    "minion": {"hp": 250, "attack": 30, "armor": 0, "reward": 1000, "next": "monster"},
    "monster": {"hp": 800, "attack": 120, "armor": 30, "reward": 2000, "next": "hero"},
    "hero": {"hp": 1800, "attack": 250, "armor": 60, "reward": 0, "next": "shop"},
}
```

`init_db(app)` executes `schema.sql` once and inserts all records with `INSERT OR IGNORE`; `create_run(app)` calls it, creates a UUID run with 7,000 HP, 350 attack implied by content, 80 armor implied by content, zero gold, one reroll token, and stage `minion`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_models.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

Run: `git add app tests && git commit -m "feat: add game database and seed content"`

### Task 3: Implement pure combat resolution

**Files:**
- Create: `app/game/__init__.py`, `app/game/combat.py`, `tests/test_combat.py`

- [ ] **Step 1: Write failing combat tests**

```python
from app.game.combat import armor_damage, advance_q, boss_q3_damage

def test_q_cycles_without_other_actions():
    assert advance_q(1) == 2
    assert advance_q(2) == 3
    assert advance_q(3) == 1

def test_all_damage_uses_one_armor_formula():
    assert armor_damage(5000, 80) == 2777

def test_exploit_build_q3_reaches_execute_threshold():
    dealt = boss_q3_damage(1490, 200, 32000, has_contract=True)
    assert dealt == 20133
    assert 32000 - dealt < 12800
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_combat.py -q`

Expected: import failure for `app.game.combat`.

- [ ] **Step 3: Implement exact formulas**

```python
# app/game/combat.py
from math import floor

def armor_damage(raw: float, armor: int) -> int:
    return floor(raw * 100 / (100 + armor))

def advance_q(stage: int) -> int:
    return 1 if stage == 3 else stage + 1

def q_raw(stage: int, attack: int) -> float:
    return {1: 200 + 1.5 * attack, 2: 350 + 2.2 * attack, 3: 600 + 4 * attack}[stage]

def boss_q3_damage(attack: int, boss_armor: int, boss_max_hp: int, has_contract: bool) -> int:
    raw = q_raw(3, attack)
    if has_contract:
        raw = raw * 7.5 + boss_max_hp * 0.35
    return armor_damage(raw, boss_armor)
```

Add a `resolve_boss_turn(state, action)` function that applies the selected action, Q stage transition, E's current incoming-hit armor, the next-three-player-turn 30% healing counter, contract execute before Mundo awakening, then Mundo's 5,000/8,000 attack and 12,800 awakening heal. Return a copied state plus ordered log messages; do not use Flask or SQLite in this module.

- [ ] **Step 4: Add and pass behavior tests**

Add tests proving E gives 180 armor only for its response turn, decrements healing after three subsequent player actions, awakening occurs only when the target survives under 12,800, and a contract execute happens first.

Run: `pytest tests/test_combat.py -q`

Expected: all combat tests pass.

- [ ] **Step 5: Commit**

Run: `git add app/game tests/test_combat.py && git commit -m "feat: add deterministic combat engine"`

### Task 4: Add game lifecycle and combat API

**Files:**
- Create: `app/routes/game.py`, `tests/test_game_routes.py`
- Modify: `app/__init__.py`, `app/models.py`

- [ ] **Step 1: Write failing route tests**

```python
def test_start_then_win_minion_unlocks_monster(client):
    run = client.post("/api/runs").get_json()["run"]
    for _ in range(4):
        response = client.post("/api/game/action", json={"action": "q"})
        if response.get_json()["run"]["stage"] == "monster":
            break
    assert response.get_json()["run"]["stage"] == "monster"
    assert response.get_json()["run"]["gold"] == 1000
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_game_routes.py -q`

Expected: `404` for `/api/runs`.

- [ ] **Step 3: Implement routes and persistence boundary**

Register a `game_bp` blueprint. `POST /api/runs` creates a run and stores its UUID in the signed session. `GET /api/state` returns a JSON snapshot containing current stage, combatant stats, gold, rerolls, inventory, augments, shards and recent logs. `POST /api/game/action` accepts only `attack`, `q`, `e`, or `r`; it loads the run, calls pure combat code, saves every returned field, logs the action, awards minion/monster gold only on first defeat, and changes stage to `shop` after hero defeat. `POST /api/boss/start` only works at `shop` and changes stage to `boss` with 32,000 boss HP. On `won=1`, state includes `flag: current_app.config["FLAG"]`; all other states omit the `flag` key.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_game_routes.py -q`

Expected: all route tests pass.

- [ ] **Step 5: Commit**

Run: `git add app/routes/game.py app/models.py app/__init__.py tests/test_game_routes.py && git commit -m "feat: add game progression and boss API"`

### Task 5: Implement the intended SQL-injection augment path

**Files:**
- Create: `app/routes/augments.py`, `tests/test_augments.py`
- Modify: `app/__init__.py`, `app/models.py`

- [ ] **Step 1: Write failing SQLi behavior tests**

```python
def test_normal_search_hides_contract(client):
    client.post("/api/runs")
    names = [row["name"] for row in client.get("/api/augments/search?q=暗裔").get_json()["results"]]
    assert "暗裔契约" not in names

def test_union_search_can_choose_hidden_contract(client):
    client.post("/api/runs")
    payload = "%' UNION SELECT id,name,rarity,description FROM augments -- "
    results = client.get("/api/augments/search", query_string={"q": payload}).get_json()["results"]
    contract = next(row for row in results if row["id"] == "darkin-contract")
    response = client.post("/api/augments/choose", json={"augment_id": contract["id"]})
    assert response.status_code == 200
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_augments.py -q`

Expected: `404` for the search endpoint.

- [ ] **Step 3: Implement only the intended vulnerable query**

`GET /api/augments/search` must create a read-only connection and execute exactly this f-string query shape:

```python
sql = f"""SELECT id, name, rarity, description
FROM augments WHERE hidden = 0 AND name LIKE '%{q}%' LIMIT 20"""
rows = conn.execute(sql).fetchall()
session["visible_augment_ids"] = [row["id"] for row in rows]
```

`POST /api/augments/choose` accepts an ID only when it is in `session["visible_augment_ids"]`, inserts it into `run_augments`, and rejects a fourth augment. Add a normal random-offer endpoint that never returns `hidden=1`; it is for UI flavor and must not be required by the solver.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_augments.py -q`

Expected: normal search hides the contract and UNION search selects it.

- [ ] **Step 5: Commit**

Run: `git add app/routes/augments.py app/models.py app/__init__.py tests/test_augments.py && git commit -m "feat: add vulnerable augment search"`

### Task 6: Implement the stable hero-reward race

**Files:**
- Create: `app/routes/rewards.py`, `tests/test_rewards.py`
- Modify: `app/db.py`, `app/__init__.py`

- [ ] **Step 1: Write the failing concurrency test**

```python
from concurrent.futures import ThreadPoolExecutor

def test_hero_claim_race_pays_more_than_once(app):
    app.config["RACE_WINDOW_MS"] = 100
    run_id = __import__("app.models", fromlist=["create_run"]).create_run(app)
    # Mark prior nodes complete and hero defeated through model helper.
    __import__("app.models", fromlist=["set_stage"]).set_stage(app, run_id, "shop")
    def claim(_):
        with app.test_client() as c:
            with c.session_transaction() as s: s["run_id"] = run_id
            return c.post("/api/rewards/hero/claim").status_code
    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(claim, range(32)))
    run = __import__("app.models", fromlist=["get_run"]).get_run(app, run_id)
    assert run["gold"] >= 30000
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_rewards.py -q`

Expected: `404` for the reward endpoint.

- [ ] **Step 3: Implement separate short transactions**

`POST /api/rewards/hero/claim` must require stage `shop`, then: (1) query `reward_claims` using connection A; (2) if absent, sleep `RACE_WINDOW_MS / 1000`; (3) use connection B to atomically increment `gold` by 3000 and `reroll_tokens` by 1; (4) use connection C to `INSERT OR IGNORE` the single claim marker. Return the current snapshot even when the marker insert was ignored. Set `PRAGMA busy_timeout=3000` on every connection and retry only `database is locked` three times with 20ms, 40ms, 80ms delays.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_rewards.py -q`

Expected: one claim row and at least ten paid rewards under 32 concurrent requests.

- [ ] **Step 5: Commit**

Run: `git add app/routes/rewards.py app/db.py app/__init__.py tests/test_rewards.py && git commit -m "feat: add hero reward race condition"`

### Task 7: Add shop and intentional duplicate-purchase accounting flaw

**Files:**
- Create: `app/routes/shop.py`, `tests/test_shop.py`
- Modify: `app/__init__.py`, `app/models.py`

- [ ] **Step 1: Write failing normal and vulnerable purchase tests**

```python
def test_batch_buy_charges_unique_ids_but_inserts_all_ids(client, app):
    run = client.post("/api/runs").get_json()["run"]
    from app.models import set_gold, set_stage
    set_gold(app, run["id"], 6500)
    set_stage(app, run["id"], "shop")
    response = client.post("/api/shop/batch-buy", json={"item_ids": ["heartsteel"] * 4 + ["bloodmail"] * 4})
    body = response.get_json()
    assert response.status_code == 200
    assert body["run"]["gold"] == 0
    assert body["stats"]["max_hp"] == 29000
    assert body["stats"]["attack"] == 1490
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_shop.py -q`

Expected: `404` for `/api/shop/batch-buy`.

- [ ] **Step 3: Implement shop behavior**

`POST /api/shop/buy` validates one item, charges its full price, enforces inventory count below six and checks `unique_group` against all stored inventory.

`POST /api/shop/batch-buy` intentionally does this:

```python
unique_ids = list(dict.fromkeys(item_ids))
selected = fetch_items(conn, unique_ids)
total = sum(item["price"] for item in selected)
if len(unique_ids) > 6 or gold < total:
    return error("invalid_purchase", 409)
for item_id in item_ids:
    conn.execute("INSERT INTO inventory(run_id, item_id) VALUES (?, ?)", (run_id, item_id))
conn.execute("UPDATE runs SET gold = gold - ? WHERE id = ?", (total, run_id))
```

`effective_stats` must sum every `inventory` row, apply all flat health first, then apply each `bloodmail` row's `floor(max_hp * 0.005)` attack. It returns exactly `{"max_hp": int, "attack": int, "armor": int}`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_shop.py -q`

Expected: the eight-ID request is charged 6500 and yields 29,000 HP / 1,490 attack.

- [ ] **Step 5: Commit**

Run: `git add app/routes/shop.py app/models.py app/__init__.py tests/test_shop.py && git commit -m "feat: add vulnerable batch item purchase"`

### Task 8: Add bounded stat anvils

**Files:**
- Create: `tests/test_anvils.py`
- Modify: `app/routes/shop.py`, `app/models.py`, `app/content.py`

- [ ] **Step 1: Write failing anvil tests**

```python
def test_anvil_costs_750_and_fourth_pick_is_rejected(client, app):
    run = client.post("/api/runs").get_json()["run"]
    from app.models import set_gold, set_stage
    set_gold(app, run["id"], 4000)
    set_stage(app, run["id"], "shop")
    for _ in range(3):
        offer = client.post("/api/shop/anvils").get_json()["offer"]
        assert client.post("/api/shop/anvils/choose", json={"stat_key": "attack"}).status_code == 200
    assert client.post("/api/shop/anvils").status_code == 409
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_anvils.py -q`

Expected: `404` for `/api/shop/anvils`.

- [ ] **Step 3: Implement anvil state machine**

`POST /api/shop/anvils` checks no unchosen offer, fewer than three chosen shards, and at least 750 gold. It randomly chooses tier by 80/19/1 probability and writes one pending offer whose JSON options are exactly `attack`, `health`, `armor` with the selected tier values. `POST /api/shop/anvils/choose` accepts only one option from that pending offer and writes `run_stat_shards`. `POST /api/shop/anvils/reroll` spends one shared `reroll_tokens` and replaces pending options with a newly rolled tier. Add shard values to `effective_stats`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_anvils.py -q`

Expected: three permanent selections succeed; the fourth returns `anvil_limit_reached`.

- [ ] **Step 5: Commit**

Run: `git add app/content.py app/models.py app/routes/shop.py tests/test_anvils.py && git commit -m "feat: add bounded stat anvils"`

### Task 9: Build the no-art browser interface

**Files:**
- Create: `app/templates/index.html`, `app/static/style.css`, `app/static/app.js`, `tests/test_ui.py`
- Modify: `app/__init__.py`

- [ ] **Step 1: Write failing HTML route test**

```python
def test_root_serves_game_shell(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Aatrox VS Dr. Mundo" in response.data
    assert b"id=\"game\"" in response.data
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py -q`

Expected: `404` for `/`.

- [ ] **Step 3: Implement the shell and API client**

The HTML must contain cards for status, map, battle log, action buttons, augment search/results, shop batch JSON input, anvil choices, and Flag. `app.js` must call `/api/state` after every action and render text with `textContent`, never `innerHTML` from server-provided names. `style.css` uses a dark background, gold accent, responsive single-column layout, and image placeholders only; no CDN asset or external request is permitted.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_ui.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit**

Run: `git add app/templates app/static app/__init__.py tests/test_ui.py && git commit -m "feat: add game web interface"`

### Task 10: Prove the intended solution end to end

**Files:**
- Create: `scripts/solve.py`, `tests/test_e2e.py`

- [ ] **Step 1: Write failing exploit-chain test**

```python
def test_intended_chain_returns_flag(live_server):
    import subprocess, sys
    result = subprocess.run([sys.executable, "scripts/solve.py", live_server], text=True, capture_output=True, check=True)
    assert "flag{test}" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_e2e.py -q`

Expected: failure because `scripts/solve.py` is absent.

- [ ] **Step 3: Implement the proof script**

The script must create one session, clear minion/monster/hero using Q actions, issue the documented UNION query, select `darkin-contract`, send 32 concurrent hero-claim requests sharing the session cookie, batch-buy four `heartsteel` plus four `bloodmail`, start Boss, use Q three times, and print only the returned Flag. It must raise a nonzero error if any expected response shape is absent.

Add a parametrized test proving each partial path fails: contract plus no duplicate gear, duplicate gear plus no contract, and three prismatic attack shards plus contract. Add a unit test that no state response includes `flag` before `won`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_e2e.py -q`

Expected: intended chain prints `flag{test}` and every partial chain fails to win.

- [ ] **Step 5: Commit**

Run: `git add scripts tests/test_e2e.py && git commit -m "test: prove intended exploit chain"`

### Task 11: Package Docker deployment and organizer documentation

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Modify: `README.md`

- [ ] **Step 1: Write failing Docker smoke test**

```bash
docker compose up --build -d
curl --fail http://localhost:8080/health
docker compose down --volumes
```

Expected before implementation: failure because no Compose file exists.

- [ ] **Step 2: Implement container files**

Use `python:3.12-slim`, create an unprivileged `ctf` user, install dependencies from `requirements.txt`, copy source, set `PYTHONDONTWRITEBYTECODE=1`, expose 8080, and run `gunicorn --workers 4 --threads 8 --bind 0.0.0.0:8080 'app:create_app()'`. Add `gunicorn>=23,<24` to requirements. Compose maps `${PORT:-8080}:8080`, injects `${FLAG:-flag{development_only}}`, and sets `RACE_WINDOW_MS=75`. `.dockerignore` excludes `.git`, `.superpowers`, caches, local DBs, and `.env`.

README must document local launch, per-team Flag injection, reset behavior, intended challenge category, authorized-use statement, and the three high-level hints without including a SQL payload.

- [ ] **Step 3: Verify Docker smoke test**

Run: `docker compose up --build -d && curl --fail http://localhost:8080/health && docker compose down --volumes`

Expected: health returns `{"ok":true}` and cleanup exits zero.

- [ ] **Step 4: Run the full verification suite**

Run: `pytest -q && docker compose up --build -d && python scripts/solve.py http://localhost:8080 && docker compose down --volumes`

Expected: all tests pass and the solver prints the Compose-injected Flag.

- [ ] **Step 5: Commit**

Run: `git add Dockerfile docker-compose.yml .dockerignore README.md requirements.txt && git commit -m "docs: package Docker CTF challenge"`

### Task 12: Final requirement audit

**Files:**
- Modify: `README.md` only if a documented command differs from observed behavior.

- [ ] **Step 1: Audit the design against implementation**

Check each requirement in `docs/superpowers/specs/2026-08-15-aatrox-vs-dr-mundo-ctf-design.md`: Docker isolation, source distribution, direct SQLi enumeration/selection, hero reward race, duplicate batch accounting, bounded anvils, three base stats, Q cycle, E behavior, Mundo values, contract weight/execute ordering, and server-only Flag.

- [ ] **Step 2: Run final evidence commands**

Run: `pytest -q && git status --short && git log --oneline -12`

Expected: all tests pass and no uncommitted production changes remain.

- [ ] **Step 3: Commit documentation correction only when audit changes it**

Run: `git add README.md && git commit -m "docs: correct challenge operations"`

Only run this command when Step 1 changed `README.md`; otherwise make no empty commit.
