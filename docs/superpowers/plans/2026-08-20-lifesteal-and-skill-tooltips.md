# Lifesteal and Skill Tooltip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make lifesteal a visible, correctly applied player stat and replace crowded skill-card descriptions with accurate LoL-style hover/focus tooltips.

**Architecture:** `stats()` derives equipment lifesteal from inventory and returns it with all other player stats. Combat applies actual post-armor damage times base lifesteal plus E's temporary 30% bonus, caps HP server-side, and reports healing to the browser. The frontend keeps cards compact and renders complete skill descriptions only in tooltip elements.

**Tech Stack:** Python, Flask, SQLite, pytest, vanilla JavaScript, CSS.

---

### Task 1: Calculate and expose equipment lifesteal

**Files:**
- Modify: `app/models.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: Write failing stat test**

```python
def test_bloodthirster_stacks_visible_lifesteal(app):
    run_id = create_run(app)
    with connect(app) as c:
        c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)", (run_id, 'bloodthirster'))
        c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)", (run_id, 'bloodthirster'))
    assert stats(app, run_id)['lifesteal'] == 40
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_core.py::test_bloodthirster_stacks_visible_lifesteal -q`

Expected: FAIL because `stats()` has no `lifesteal` key.

- [ ] **Step 3: Implement stat derivation**

In `stats()`, initialize `lifesteal = 0`; for each inventory ID with `ITEMS[id][5] == 'lifesteal_20'`, add 20. Return integer `lifesteal` with attack, max_hp, and armor.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_core.py::test_bloodthirster_stacks_visible_lifesteal -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_core.py
git commit -m "feat: expose equipment lifesteal"
```

### Task 2: Apply base and E lifesteal to actual combat damage

**Files:**
- Modify: `app/game/combat.py`
- Modify: `app/routes/game.py`
- Modify: `tests/test_pokemon_combat.py`

- [ ] **Step 1: Write failing combat test**

```python
def test_lifesteal_combines_equipment_and_e_bonus():
    state = resolve_turn({'q_stage': 1, 'hp': 1000, 'e_lifesteal_turns': 3, 'r_turns': 0}, 'q', 350, 80, 0, 0, [0.0, 0.9], lifesteal=20, max_hp=7000)
    assert state['healing'] == int(state['damage'] * .50)
    assert state['hp'] == 1000 + state['healing']
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_pokemon_combat.py::test_lifesteal_combines_equipment_and_e_bonus -q`

Expected: FAIL because `resolve_turn` accepts no lifesteal/max_hp parameters and reports no healing.

- [ ] **Step 3: Implement capped healing**

Add optional `lifesteal=0` and `max_hp=None` parameters to `resolve_turn`. On Q/W damage, compute `healing = floor(dealt * ((lifesteal + (30 if e_lifesteal_turns else 0)) / 100))`, cap state HP at `max_hp` when supplied, expose `state['healing']`, and decrement E turns only after a damaging player action. Pass `stats()['lifesteal']` and max HP from `action`; include `healing` in its JSON response.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_pokemon_combat.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/game/combat.py app/routes/game.py tests/test_pokemon_combat.py
git commit -m "feat: apply lifesteal in combat"
```

### Task 3: Show lifesteal and concise skill cards with detailed tooltips

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing UI contract test**

```python
def test_player_ui_shows_lifesteal_and_full_skill_tooltips(client):
    javascript = client.get('/static/app.js').data
    assert '吸血 ${stats.lifesteal}%'.encode() in javascript
    assert '三段斩击'.encode() in javascript
    assert '200 + 150%攻击'.encode() in javascript
    assert b'skill-tooltip' in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_ui_shows_lifesteal_and_full_skill_tooltips -q`

Expected: FAIL because the HUD lacks lifesteal and tooltips only contain short tactical notes.

- [ ] **Step 3: Implement player-facing stat and skill metadata**

Render `吸血 ${stats.lifesteal}%` in `renderTopbar()`. Update `SKILL_INFO` so card summary is at most three short words, while tooltip text contains the exact current-rule descriptions: Q three damage values and contract note; W 250+100% attack, 70%, next enemy attack -20%; E +100 armor and 30% extra lifesteal for three turns; R +25% attack for three turns. Render tooltip `effect` and `tactical` text only inside `.skill-tooltip`.

- [ ] **Step 4: Render healing floats from response**

Use `data.healing` directly after combat action to call `showFloatText(..., '+${data.healing}', 'heal')`; do not infer healing from net HP change because enemy retaliation can mask it.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_ui_shows_lifesteal_and_full_skill_tooltips -q && node --check app/static/app.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: show lifesteal and detailed skill tooltips"
```

### Task 4: Full regression verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document visible lifesteal**

Add a concise player-facing README sentence: equipment lifesteal is visible in the stat panel and E temporarily adds more lifesteal.

- [ ] **Step 2: Verify complete flow**

Run:

```bash
pytest -q
node --check app/static/app.js
FLAG='flag{docker_test}' docker compose up --build -d
sleep 4
python scripts/solve.py http://127.0.0.1:8080
docker compose down --volumes
```

Expected: all tests pass, no JavaScript syntax errors, and solver prints `flag{docker_test}`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: describe visible lifesteal"
```
