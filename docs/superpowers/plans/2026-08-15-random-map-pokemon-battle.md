# Random Map and Pokémon Battle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the linear game with a 12-floor seeded branching map, campfire-only Hex acquisition, and hidden-move four-skill battles while preserving the intended CTF chain.

**Architecture:** Persist generated nodes, directed edges, node state, campfire candidates, and battle state in SQLite. Keep combat deterministic apart from an injected RNG interface for accuracy/dodge tests; routes only validate node transitions and persist transitions. The existing SQLi moves from `/api/augments` to the active campfire meditation search, while reward race and batch-buy remain scoped to hero and shop nodes.

**Tech Stack:** Python 3.12, Flask, SQLite, pytest, vanilla JavaScript, Docker Compose.

---

### Task 1: Persist seeded 12-floor maps

**Files:**
- Modify: `app/db.py`, `app/models.py`, `app/content.py`, `app/routes/game.py`
- Create: `app/game/mapgen.py`, `tests/test_mapgen.py`

- [ ] **Step 1: Write failing connectivity test**

```python
def test_generated_map_has_twelve_floors_and_required_route(app):
    from app.models import create_run, map_snapshot
    run_id = create_run(app, seed=7)
    graph = map_snapshot(app, run_id)
    assert max(node["floor"] for node in graph["nodes"]) == 12
    assert graph["required_route"] == ["hero", "shop", "campfire", "boss"]
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_mapgen.py -q`

Expected: failure because `map_snapshot` does not exist.

- [ ] **Step 3: Implement map tables and generator**

Add `seed` and `status` to `runs`; add `map_nodes`, `map_edges`, and `run_map_state` exactly as documented in the design. `generate_map(seed)` returns floors 1–12, 2–3 nodes per non-Boss floor, and edges only from floor N to N+1. Force one path containing a hero node before a shop node before a campfire node; set Boss as the only floor-12 node. Insert the graph in `create_run`, start at the floor-1 node, and expose it from `GET /api/map`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_mapgen.py -q`

Expected: maps for seeds 1–100 are connected and all contain the required route.

- [ ] **Step 5: Commit**

Run: `git add app tests/test_mapgen.py && git commit -m "feat: add seeded branching map"`

### Task 2: Enforce node movement and permanent run failure

**Files:**
- Modify: `app/models.py`, `app/routes/game.py`
- Create: `tests/test_map_routes.py`

- [ ] **Step 1: Write failing movement/failure tests**

```python
def test_only_adjacent_node_can_be_entered(client):
    client.post("/api/runs")
    graph = client.get("/api/map").get_json()["map"]
    blocked = next(node["id"] for node in graph["nodes"] if node["floor"] == 4)
    assert client.post(f"/api/map/enter/{blocked}").status_code == 409

def test_dead_run_rejects_all_game_actions(client, app):
    run = client.post("/api/runs").get_json()["run"]
    from app.models import set_run_status
    set_run_status(app, run["id"], "failed")
    assert client.post("/api/game/action", json={"action":"q"}).get_json()["error"] == "run_failed"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_map_routes.py -q`

Expected: missing map endpoint and `run_failed` behavior.

- [ ] **Step 3: Implement guards**

`POST /api/map/enter/<node_id>` must accept only an unvisited node linked from `run_map_state.current_node_id`; it changes that state, marks the prior node left, and creates a battle only for combat node types. Centralize `require_active_run()` and call it in game, shop, rewards, campfire, and augment routes. When player HP reaches zero, set status `failed`; never reset HP, enemy HP, or map state.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_map_routes.py -q`

Expected: non-adjacent movement and every action on a failed run return 409.

- [ ] **Step 5: Commit**

Run: `git add app tests/test_map_routes.py && git commit -m "feat: enforce map traversal and run failure"`

### Task 3: Replace combat actions with Q/W/E/R and accuracy

**Files:**
- Modify: `app/game/combat.py`, `app/routes/game.py`, `app/models.py`
- Create: `tests/test_pokemon_combat.py`

- [ ] **Step 1: Write failing four-move tests**

```python
def test_w_hit_debuffs_exactly_one_enemy_attack():
    from app.game.combat import resolve_turn
    first = resolve_turn({"rng": [0.1, 0.9]}, "w", enemy_attack=5000, attack=350, armor=80)
    assert first["w_debuff_pending"] is True
    second = resolve_turn(first, "e", enemy_attack=5000, attack=350, armor=80)
    assert second["enemy_raw_attack"] == 4000

def test_q_misses_at_ninety_percent_boundary():
    from app.game.combat import accuracy_hit
    assert accuracy_hit(0.89, 0.90) is True
    assert accuracy_hit(0.90, 0.90) is False
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_pokemon_combat.py -q`

Expected: missing `resolve_turn` and `accuracy_hit`.

- [ ] **Step 3: Implement battle state transitions**

Create `battles(run_id,node_id,enemy_key,enemy_hp,turn,w_debuff_pending,e_lifesteal_turns,r_turns,status)`. `resolve_turn` accepts injected random rolls and returns structured log entries. Q has 90% hit and cycles Q1/Q2/Q3/Q1; W has 70% hit and applies a one-enemy-attack 20% reduction only on hit; E creates one-response +100 armor and three future player-turn 30% healing; R has three player turns of +25% attack. Enemy attacks always hit, but a player dodge roll `< 0.10` ignores their damage/effect. Do not expose the chosen enemy move until after resolution.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_pokemon_combat.py -q`

Expected: Q/W boundaries, W duration, E/R duration, dodge, hidden move log ordering, and Boss contract execute tests pass.

- [ ] **Step 5: Commit**

Run: `git add app tests/test_pokemon_combat.py && git commit -m "feat: add hidden move four-skill battles"`

### Task 4: Make campfires the only Hex source and relocate SQLi

**Files:**
- Modify: `app/routes/augments.py`, `app/routes/game.py`, `app/models.py`, `app/static/app.js`
- Create: `app/routes/campfires.py`, `tests/test_campfires.py`

- [ ] **Step 1: Write failing campfire tests**

```python
def test_meditation_is_only_hex_source_and_sqli_selects_contract(client):
    node = enter_required_campfire(client)
    offer = client.post(f"/api/campfires/{node}/meditate").get_json()["offer"]
    assert len(offer) == 3
    payload = "%' UNION SELECT id,name,rarity,description FROM augments -- "
    rows = client.get(f"/api/campfires/{node}/meditate/search", query_string={"q":payload}).get_json()["results"]
    assert any(row["id"] == "darkin-contract" for row in rows)
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_campfires.py -q`

Expected: missing campfire endpoints.

- [ ] **Step 3: Implement one-use campfires**

Create `campfire_offers`. `POST /api/campfires/<id>/rest` restores computed max HP and closes the node. `POST /api/campfires/<id>/meditate` creates three public IDs; `/reroll` costs one run refresh token; `/search` performs the only vulnerable f-string query; `/choose` only permits an ID in the campfire's candidate set and closes the node. Remove `/api/augments/search` and `/api/augments/choose`; no shop or combat endpoint may insert `run_augments`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_campfires.py -q`

Expected: rest blocks meditation, three choices are public by default, SQLi allows contract choice, and no other endpoint grants a Hex.

- [ ] **Step 5: Commit**

Run: `git add app tests/test_campfires.py && git commit -m "feat: restrict Hexes to campfire meditation"`

### Task 5: Migrate CTF chain, UI, solver, and Docker verification

**Files:**
- Modify: `app/routes/rewards.py`, `app/routes/shop.py`, `app/templates/index.html`, `app/static/app.js`, `app/static/style.css`, `scripts/solve.py`, `README.md`
- Create: `tests/test_random_map_e2e.py`

- [ ] **Step 1: Write failing end-to-end test**

```python
def test_seeded_map_exploit_chain_returns_flag(live_server):
    result = run_solver(live_server, seed=17)
    assert result.stdout.strip() == "flag{test}"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_random_map_e2e.py -q`

Expected: old solver cannot traverse map/campfire API.

- [ ] **Step 3: Implement migration**

Render clickable connected map nodes and a Pokémon-like four-button battle panel; render campfire rest/meditate/refresh/choose controls only at an active campfire. Bind hero reward claim only after its hero node battle; bind batch-buy only at a shop node. Update solver to choose the generator-guaranteed hero→shop→campfire route, SQLi the meditation query, race 32 hero claims, buy four heartsteels plus four bloodmails, and complete the Boss Q cycle. Update README with new map, failure, and campfire rules.

- [ ] **Step 4: Verify GREEN and Docker**

Run: `pytest -q && FLAG='flag{docker_test}' docker compose up --build -d && sleep 3 && python scripts/solve.py http://127.0.0.1:8080 && docker compose down --volumes`

Expected: test suite passes; solver prints `flag{docker_test}`.

- [ ] **Step 5: Commit**

Run: `git add app scripts tests README.md && git commit -m "feat: ship random map CTF experience"`
