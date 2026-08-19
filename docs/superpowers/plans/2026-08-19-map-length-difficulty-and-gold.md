# 25-Floor Map, Difficulty, and Gold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a 25-floor locally connected roguelike map with meaningful enemy pressure and explicit server-side battle gold drops while preserving the CTF solve chain.

**Architecture:** Replace the map generator's all-to-all edges with seeded node placement and 1–2 local forward edges, while constructing one guaranteed valid anchor route. Derive non-Boss enemy stats and rewards from the current map node floor, persist no extra combat data, and return `gold_reward` from the existing action endpoint for the player victory summary.

**Tech Stack:** Python 3.12, Flask, SQLite, pytest, vanilla JavaScript, Docker Compose.

---

### Task 1: Generate locally connected 25-floor maps

**Files:**
- Modify: `app/game/mapgen.py`
- Modify: `tests/test_mapgen.py`

- [ ] **Step 1: Write failing topology tests**

```python
def test_generated_map_has_twenty_five_floors_and_variable_row_widths():
    nodes, _ = generate_map(7)
    rows = {floor: [node for node in nodes if node['floor'] == floor] for floor in range(1, 26)}
    assert len(rows[1]) == len(rows[25]) == 1
    assert all(2 <= len(rows[floor]) <= 4 for floor in range(2, 25))

def test_adjacent_rows_are_not_fully_connected():
    nodes, edges = generate_map(11)
    row2 = [node['id'] for node in nodes if node['floor'] == 2]
    row3 = [node['id'] for node in nodes if node['floor'] == 3]
    between = [(left, right) for left, right in edges if left in row2 and right in row3]
    assert len(between) < len(row2) * len(row3)
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_mapgen.py -q`

Expected: FAIL because the current generator has 12 floors and full cross-row edges.

- [ ] **Step 3: Implement seeded row generation and local edge selection**

In `generate_map(seed)`, generate floors 1 through 25. Use one node on floors 1/25, two nodes on floors 2–7, three nodes on floors 8–17, and `rng.randint(3,4)` nodes on floors 18–24. For each source index in a row, choose one forward destination from indexes `[index-1,index,index+1]` clamped to the next row; add a second only with `rng.random() < .35`. Ensure every next-row node has an incoming edge by adding its nearest previous-row source when needed.

Anchor one route with forced types at floors 8 `hero`, 14 `shop`, 20 `campfire`, and 25 `boss`; set the corresponding route nodes before randomizing all remaining non-start nodes.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_mapgen.py -q`

Expected: PASS; maps from seeds 1–100 have 25 floors, only next-floor edges, no full adjacent-row connections, and an anchor route containing hero/shop/campfire/Boss in order.

- [ ] **Step 5: Commit**

```bash
git add app/game/mapgen.py tests/test_mapgen.py
git commit -m "feat: generate 25-floor local maps"
```

### Task 2: Derive battle stats and rewards from floor

**Files:**
- Modify: `app/content.py`
- Modify: `app/models.py`
- Modify: `app/routes/game.py`
- Create: `tests/test_difficulty.py`

- [ ] **Step 1: Write failing scaling tests**

```python
def test_late_floor_elite_is_stronger_than_early_floor_elite():
    from app.content import enemy_for_floor
    assert enemy_for_floor('monster', 20)['hp'] > enemy_for_floor('monster', 5)['hp']
    assert enemy_for_floor('monster', 20)['attack'] > enemy_for_floor('monster', 5)['attack']

def test_floor_reward_increases_by_tier():
    from app.content import enemy_for_floor
    assert enemy_for_floor('minion', 14)['reward'] > enemy_for_floor('minion', 2)['reward']
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_difficulty.py -q`

Expected: FAIL because `enemy_for_floor` does not exist.

- [ ] **Step 3: Implement `enemy_for_floor`**

Define `enemy_for_floor(enemy_key, floor)` in `app/content.py`. Start with bases `{minion:(900,420,25,700,250), monster:(1600,720,60,1400,400), hero:(3600,1050,95,3000,700)}`. Calculate `tier = floor // 6`; add `hp_step*tier`, `attack_step*tier`, `armor_step*tier`, and `reward_step*tier` using `(260,110,15)`, `(420,170,20)`, and `(650,240,25)` per enemy type. On floors 17–24 multiply HP/attack by the specified enemy-type pressure multipliers from the design; return integer `hp`, `attack`, `armor`, and `reward`.

Add `current_map_node(app, run_id)` in `app/models.py`, returning the current node row. In `enter_node`, use its floor and `enemy_for_floor` to initialize `runs.enemy_hp` for normal/elite/hero nodes. In `action`, use `enemy_for_floor` for enemy armor, attack, and reward instead of static `ENEMIES` values.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_difficulty.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/content.py app/models.py app/routes/game.py tests/test_difficulty.py
git commit -m "feat: scale enemy pressure by floor"
```

### Task 3: Return and display battle gold drops

**Files:**
- Modify: `app/routes/game.py`
- Modify: `app/static/app.js`
- Modify: `tests/test_difficulty.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing gold-drop tests**

```python
def test_non_boss_victory_returns_and_adds_floor_gold(client, app, monkeypatch):
    run, node = enter_combat_node(client, app, kind='normal', floor=2)
    monkeypatch.setattr('app.routes.game.random.random', lambda: 0.0)
    response = client.post('/api/game/action', json={'action': 'q'}).get_json()
    assert response['gold_reward'] > 0
    assert response['run']['gold'] == response['gold_reward']
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_difficulty.py::test_non_boss_victory_returns_and_adds_floor_gold -q`

Expected: FAIL because action responses have no `gold_reward`.

- [ ] **Step 3: Implement explicit reward response**

Initialize `gold_reward = 0` in `action`. When a non-Boss target dies, calculate the floor-derived reward once, add it to `run['gold']`, assign it to `gold_reward`, and include `gold_reward=gold_reward` in the JSON response. Keep it zero for Boss and non-lethal actions.

In battle action handling in `app/static/app.js`, when `data.gold_reward > 0`, append `胜利！获得 ${data.gold_reward} 金币。` to the activity log before refreshing the map.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_difficulty.py tests/test_ui.py -q && node --check app/static/app.js`

Expected: PASS with no JavaScript syntax output.

- [ ] **Step 5: Commit**

```bash
git add app/routes/game.py app/static/app.js tests/test_difficulty.py tests/test_ui.py
git commit -m "feat: show floor-scaled battle gold"
```

### Task 4: Update solver and verify full flow

**Files:**
- Modify: `scripts/solve.py`
- Modify: `README.md`

- [ ] **Step 1: Update route traversal assumptions**

Change no fixed-floor or fixed-ID assumptions in `scripts/solve.py`. Select only from outgoing edges and prioritize the next guaranteed route type (`hero`, then `shop`, then `campfire`, then Boss); handle all incidental normal/elite/hero battles and event nodes through existing helpers.

- [ ] **Step 2: Document 25-floor player flow**

Update README to state that a full run is a 25-floor, locally connected route with escalating combat rewards; do not disclose exploit payloads.

- [ ] **Step 3: Full verification**

Run:

```bash
pytest -q
node --check app/static/app.js
FLAG='flag{docker_test}' docker compose up --build -d
sleep 4
python scripts/solve.py http://127.0.0.1:8080
docker compose down --volumes
```

Expected: all tests pass, JavaScript syntax check emits nothing, and solver prints `flag{docker_test}`.

- [ ] **Step 4: Commit**

```bash
git add scripts/solve.py README.md
git commit -m "feat: ship longer escalating roguelike map"
```
