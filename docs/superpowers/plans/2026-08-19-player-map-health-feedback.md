# Player Map, Health, and Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a player-readable 25-floor SVG map, accurate enemy health, reliable restart, combat float text, Chinese skill explanations, and actionable feedback without changing CTF APIs.

**Architecture:** Add `enemy_max_hp` to the persisted run and return it in existing snapshots. The frontend renders map geometry from server-provided nodes/edges in one SVG layer, renders information tooltips from local player-facing view metadata, and maps server errors to Chinese action messages. A single `startNewRun()` initializes any new run so landing and modal actions share reliable behavior.

**Tech Stack:** Flask, SQLite, pytest, vanilla JavaScript, CSS/SVG, Docker Compose.

---

### Task 1: Increase map density and persist actual enemy maximum HP

**Files:**
- Modify: `app/game/mapgen.py`
- Modify: `app/db.py`
- Modify: `app/routes/game.py`
- Modify: `tests/test_mapgen.py`
- Create: `tests/test_enemy_health.py`

- [ ] **Step 1: Write failing density and health tests**

```python
def test_middle_rows_have_four_to_six_nodes():
    nodes, _ = generate_map(9)
    rows = {floor: [n for n in nodes if n['floor'] == floor] for floor in range(2, 25)}
    assert all(4 <= len(row) <= 6 for row in rows.values())

def test_entering_combat_writes_actual_enemy_max_hp(client):
    node = enter_normal_node(client)
    run = client.get('/api/state').get_json()['run']
    assert run['enemy_hp'] == run['enemy_max_hp']
    assert run['enemy_max_hp'] > 0
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_mapgen.py tests/test_enemy_health.py -q`

Expected: FAIL because rows have 2–4 nodes and `enemy_max_hp` does not exist.

- [ ] **Step 3: Implement density and max-HP persistence**

Make `row_width` return 4–6 for every floor 2–24 while retaining one start and one Boss. Add `enemy_max_hp INTEGER NOT NULL DEFAULT 0` to `runs`. On non-Boss combat node entry, set `enemy_hp` and `enemy_max_hp` to `enemy_for_floor(...)["hp"]`; reset both to zero for non-combat nodes. On Boss entry set `boss_hp=32000`; the UI uses that fixed Boss maximum.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_mapgen.py tests/test_enemy_health.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/game/mapgen.py app/db.py app/routes/game.py tests/test_mapgen.py tests/test_enemy_health.py
git commit -m "feat: persist enemy max health and denser map"
```

### Task 2: Render SVG-connected map with useful node information

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing SVG-map contract test**

```python
def test_player_script_renders_svg_map_edges_and_node_information(client):
    javascript = client.get('/static/app.js').data
    assert b'<svg' in javascript
    assert b'<line' in javascript
    assert b'NODE_INFO' in javascript
    assert '第 ${node.floor} 层'.encode() in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_renders_svg_map_edges_and_node_information -q`

Expected: FAIL because the current map uses only row buttons.

- [ ] **Step 3: Implement geometry and SVG rendering**

Implement `mapPoint(node, rows)` returning a shared pixel coordinate with `x = 90 + index * horizontalSpacing` and `y = 80 + (floor - 1) * 104`. `renderMapScene()` creates a positioned `.map-canvas`, adds SVG lines for every `map.edges` pair, then positions actual accessible `<button>` nodes over the same coordinates. Lines leaving the current node receive `route-active`; lines from left/cleared nodes receive `route-cleared`.

Define Chinese `NODE_INFO` for every node type with `title`, `risk`, and `reward`; node buttons include this text in a tooltip and `aria-label`. Use a scrollable map viewport on narrow screens.

- [ ] **Step 4: Style SVG and map nodes**

Add `.map-viewport`, `.map-canvas`, `.map-lines`, `.map-line`, `.route-active`, `.route-cleared`, `.map-node-dot`, `.node-tooltip`, plus type-specific node colors. SVG and button coordinate systems must share the fixed canvas width.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_renders_svg_map_edges_and_node_information -q && node --check app/static/app.js`

Expected: PASS with no JavaScript syntax output.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: render connected player map"
```

### Task 3: Improve battle feedback and reliable restart

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing interaction contract test**

```python
def test_player_script_has_restart_and_combat_float_text(client):
    javascript = client.get('/static/app.js').data
    assert b'async function startNewRun' in javascript
    assert b'function showFloatText' in javascript
    assert b'enemy_max_hp' in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_has_restart_and_combat_float_text -q`

Expected: FAIL because restart is wired through a removed start button and no float renderer exists.

- [ ] **Step 3: Implement restart, health display, and float text**

Replace direct `#start.click()` calls with `startNewRun()`. It resets `gameState` scene-only fields, posts `/api/runs`, refreshes map, and renders map scene. Make the landing button call it.

For non-Boss health bars use `run.enemy_hp / run.enemy_max_hp`; retain `run.boss_hp / 32000` for Boss. Before an action save player HP; after response call `showFloatText('.combatant.enemy', '-${data.damage}', 'damage')`, `showFloatText('.combatant.player-tooltip', '-${data.enemy_damage}', 'damage-taken')`, and if current player HP rose, `showFloatText(..., '+${heal}', 'heal')`. `showFloatText` appends one `.float-text`, then removes it on `animationend`.

- [ ] **Step 4: Style floats and result modals**

Add `.float-text`, `.float-text.damage`, `.float-text.damage-taken`, `.float-text.heal`, and `@keyframes float-up`. Keep player and enemy combatants `position:relative`.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_has_restart_and_combat_float_text -q && node --check app/static/app.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: add restart and combat float text"
```

### Task 4: Localize skill and action feedback for players

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing player-information test**

```python
def test_player_script_defines_skill_and_purchase_explanations(client):
    javascript = client.get('/static/app.js').data
    assert b'SKILL_INFO' in javascript
    assert b'PURCHASE_ERRORS' in javascript
    assert '命中率'.encode() in javascript
    assert '金币不足'.encode() in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_defines_skill_and_purchase_explanations -q`

Expected: FAIL because raw error strings are logged and skills lack tooltips.

- [ ] **Step 3: Implement Chinese information and feedback**

Add `SKILL_INFO` for Q/W/E/R containing title, effect, accuracy, duration, and tactical note. In battle card markup show summary and a hidden-on-default `.skill-tooltip` that opens on hover/focus.

Add `PURCHASE_ERRORS` mapping: `invalid_purchase` → `金币不足、背包已满或装备规则冲突。请检查金币与已装备物品。`; `stage_locked` → `此处无法购买。请先进入商店节点。`; `invalid_id` → `该物品不存在。请重新选择。`. Make `api()` open a Chinese modal for shop/anvil errors and log Chinese messages for all other errors; never show raw keys to the player.

- [ ] **Step 4: Style tooltips and feedback modal**

Add `.skill-tooltip`, `.move-card:hover .skill-tooltip`, `.move-card:focus-within .skill-tooltip`, and `.feedback-modal`. Ensure tooltip details are keyboard reachable.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_defines_skill_and_purchase_explanations -q && node --check app/static/app.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: explain player actions in Chinese"
```

### Task 5: Complete verification and documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add player UI note**

Document that the 25-floor map shows only actual links and that combat values, skill tooltips, and purchase feedback are player-facing Chinese information. Do not describe payloads or vulnerable request details.

- [ ] **Step 2: Run full verification**

Run:

```bash
pytest -q
node --check app/static/app.js
FLAG='flag{docker_test}' docker compose up --build -d
sleep 4
python scripts/solve.py http://127.0.0.1:8080
docker compose down --volumes
```

Expected: all tests pass, JavaScript syntax check emits nothing, and the solver prints `flag{docker_test}`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: describe player-facing map feedback"
```
