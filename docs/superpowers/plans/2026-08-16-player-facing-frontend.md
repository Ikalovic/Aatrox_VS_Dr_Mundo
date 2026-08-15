# Player-Facing Three-Scene Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the debug-like game page with a responsive map, battle, and event experience for players while preserving every existing CTF API and server rule.

**Architecture:** Keep Flask and its APIs unchanged. `app/static/app.js` owns a small client-side scene selector based on `run.stage`, renders semantic HTML from map/state responses, and converts action results into concise player logs. `index.html` provides scene containers only; CSS defines the visual system and responsive layout without asset dependencies, with explicit image placeholder slots.

**Tech Stack:** Flask templates, vanilla JavaScript, CSS, pytest, Node syntax check, Docker Compose.

---

### Task 1: Establish player-facing page structure

**Files:**
- Modify: `app/templates/index.html`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing structural test**

```python
def test_root_has_player_scene_shells(client):
    html = client.get('/').data
    assert b'id="topbar"' in html
    assert b'id="scene-map"' in html
    assert b'id="scene-battle"' in html
    assert b'id="scene-event"' in html
    assert b'id="activity-log"' in html
    assert b'id="debug"' not in html
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_root_has_player_scene_shells -q`

Expected: FAIL because the three scene containers and activity log do not exist.

- [ ] **Step 3: Replace the debug shell with semantic scene containers**

Use this structure in `app/templates/index.html`:

```html
<header id="topbar"><div class="brand">暗裔远征</div><div id="run-stats"></div></header>
<main id="game-shell">
  <section id="scene-map" class="scene" aria-live="polite"></section>
  <section id="scene-battle" class="scene" aria-live="polite" hidden></section>
  <section id="scene-event" class="scene" aria-live="polite" hidden></section>
</main>
<aside id="activity-log" aria-label="冒险记录"></aside>
<div id="modal-root"></div>
```

Keep only the initial `开始远征` button in the map scene. Do not add JSON `<pre>` elements, an explicit boss-start button, or a visible batch JSON input.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_ui.py::test_root_has_player_scene_shells -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/index.html tests/test_ui.py
git commit -m "feat: add player scene shell"
```

### Task 2: Render map and persistent player HUD

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing UI contract test**

```python
def test_player_shell_uses_scene_renderer_contract(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderMapScene' in javascript
    assert b'function renderTopbar' in javascript
    assert b'current_node_id' in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_shell_uses_scene_renderer_contract -q`

Expected: FAIL because the current script has no scene rendering functions.

- [ ] **Step 3: Implement state, HUD, and map renderer**

In `app/static/app.js`, create `gameState = { run: null, stats: null, map: null, logs: [] }`; define `renderTopbar()` and `renderMapScene()`. `renderTopbar()` must render gold, HP, attack, armor, and reroll tokens. `renderMapScene()` must read `gameState.map.current_node_id`, calculate outgoing edge IDs, and render each floor as a row of buttons. Only outgoing nodes may be enabled.

Use a node label map such as:

```javascript
const NODE_LABELS = {start: '起点', normal: '小兵', elite: '精英', hero: '英雄', shop: '商店', campfire: '篝火', event: '事件', boss: '蒙多'};
```

Every map click calls `POST /api/map/enter/<id>`, updates state from the response, fetches `/api/map`, then calls `renderApp()`.

- [ ] **Step 4: Style the HUD and vertical map**

Add CSS classes `.topbar`, `.stat-pill`, `.map-floor`, `.map-node`, `.map-node.reachable`, `.map-node.cleared`, `.map-node.current`, and responsive rules below `700px`. Add text-only `<div class="portrait-placeholder">剑魔 / 敌方肖像待补充</div>` slots; do not reference absent image paths.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_shell_uses_scene_renderer_contract -q && node --check app/static/app.js`

Expected: PASS with no JavaScript syntax output.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: render player HUD and map"
```

### Task 3: Build Pokémon-style battle scene

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing battle renderer test**

```python
def test_player_script_defines_battle_scene_with_four_moves(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderBattleScene' in javascript
    for move in (b'Q', b'W', b'E', b'R'):
        assert move in javascript
    assert b'player-tooltip' in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_defines_battle_scene_with_four_moves -q`

Expected: FAIL because `renderBattleScene` and tooltip markup do not exist.

- [ ] **Step 3: Implement battle renderer and result logging**

Implement `renderBattleScene()` for `minion`, `monster`, `hero`, and `boss` stages. It must display a top health strip, left player card, right enemy card, tooltips with HP/attack/armor on focus and hover, and four action buttons in a two-by-two grid. The Q/W/E/R buttons call `/api/game/action`; use returned `hit`, `damage`, and `enemy_damage` to append one short Chinese sentence to `gameState.logs` rather than displaying the raw response.

For enemy display use local stage metadata:

```javascript
const ENEMY_VIEW = {minion: ['小兵', 250], monster: ['野怪', 800], hero: ['敌方英雄', 1800], boss: ['蒙多', 32000]};
```

After an action, refresh `/api/map`; if `run.status === 'failed'`, open a modal with a single `重开一局` button. If `flag` exists, open a victory modal that shows the flag.

- [ ] **Step 4: Style battle as a two-sided arena**

Add `.battle-arena`, `.combatant`, `.combatant.enemy`, `.health-bar`, `.health-fill`, `.move-grid`, `.move-card`, `.tooltip`, and focus-visible styles. Above 700px player/enemy cards are a row; below 700px they stack. No image must be required for the arena to render.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_defines_battle_scene_with_four_moves -q && node --check app/static/app.js`

Expected: PASS with no JavaScript syntax output.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: add player battle scene"
```

### Task 4: Build card-based shop and campfire events

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing event renderer test**

```python
def test_player_script_defines_card_based_event_scenes(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderShopEvent' in javascript
    assert b'function renderCampfireEvent' in javascript
    assert b'采购清单' in javascript
    assert b'研究档案' in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_defines_card_based_event_scenes -q`

Expected: FAIL because event scene functions are absent.

- [ ] **Step 3: Implement shop and campfire event renderers**

`renderShopEvent()` must render four item cards using a local display table matching server IDs/prices, a single-purchase button for each, the 750-gold anvil button, hero loot claim when available, and a closed `<details>` block labelled `采购清单` containing the existing batch request control.

`renderCampfireEvent()` must initially render rest and meditate cards. After meditation, render the returned offer as three selectable Hex cards and a reroll button. Put the existing vulnerable search request behind a closed `<details>` labelled `研究档案`; it sends `GET /api/campfires/<currentNode>/meditate/search?q=` and replaces only the candidate cards.

Each successful event action calls `refreshMap()` then `renderApp()`; a closed campfire returns the player to the map scene.

- [ ] **Step 4: Style event cards and disclosure panels**

Add `.event-panel`, `.choice-card`, `.choice-grid`, `.item-card`, `.hex-card`, `.details-panel`, `.gold-cost`, `.rare`, `.prismatic` and hover/focus styles. Ensure disclosure panels are visibly secondary and never expanded by default.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_defines_card_based_event_scenes -q && node --check app/static/app.js`

Expected: PASS with no JavaScript syntax output.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: add player event cards"
```

### Task 5: Verify player flow and Docker regression chain

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing anti-debug-page test**

```python
def test_root_does_not_expose_raw_debug_controls(client):
    html = client.get('/').data
    assert b'id="log"' not in html
    assert b'id="boss"' not in html
    assert b'JSON.stringify' not in html
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_root_does_not_expose_raw_debug_controls -q`

Expected: FAIL until the old debug IDs and raw log markup are removed.

- [ ] **Step 3: Document the player UI**

Add a README section describing map → battle → event flow, the hover/focus attribute cards, and the fact that image placeholders can be replaced later without changing gameplay. Do not document exploit payloads.

- [ ] **Step 4: Verify GREEN and end-to-end behavior**

Run:

```bash
pytest -q
node --check app/static/app.js
FLAG='flag{docker_test}' docker compose up --build -d
sleep 4
python scripts/solve.py http://127.0.0.1:8080
docker compose down --volumes
```

Expected: all pytest tests pass, syntax check emits nothing, solver prints `flag{docker_test}`, and Docker is stopped afterward.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_ui.py app/templates/index.html app/static/app.js app/static/style.css
git commit -m "feat: ship player-facing game frontend"
```
