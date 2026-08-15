# Random Event Nodes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn event map nodes into persistent, one-time mixed reward/risk choices without adding any new Hex source.

**Architecture:** SQLite stores a generated event offer per `(run_id,node_id)` and its chosen key. A dedicated Flask blueprint validates the current event node, atomically applies server-side reward effects, and closes the node. The existing frontend scene selector queries this API and renders cards only for active event nodes.

**Tech Stack:** Flask, SQLite, pytest, vanilla JavaScript, CSS, Docker Compose.

---

### Task 1: Persist event offers and server-side reward effects

**Files:**
- Modify: `app/db.py`
- Create: `app/routes/events.py`
- Modify: `app/__init__.py`
- Create: `tests/test_events.py`

- [ ] **Step 1: Write failing persistence test**

```python
def test_current_event_returns_persisted_offer(client, app):
    node = make_event_current(client, app)
    first = client.get(f'/api/events/{node}').get_json()['offer']
    second = client.get(f'/api/events/{node}').get_json()['offer']
    assert first == second
    assert first['event_key'] in {'loot', 'altar', 'relic'}
```

`make_event_current` creates a run and updates its current map node to an event node in a test-only database helper.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_events.py::test_current_event_returns_persisted_offer -q`

Expected: FAIL because `/api/events/<node>` is not registered.

- [ ] **Step 3: Add table and event offer generator**

Append this table to `SCHEMA` in `app/db.py`:

```sql
CREATE TABLE IF NOT EXISTS node_events (
  run_id TEXT NOT NULL, node_id TEXT NOT NULL, event_key TEXT NOT NULL,
  offer_json TEXT NOT NULL, chosen_key TEXT,
  PRIMARY KEY (run_id, node_id)
);
```

In `app/routes/events.py`, register `bp = Blueprint('events', __name__)`; generate one randomly selected offer using these literal records:

```python
OFFERS = {
  'loot': {'title': '战利品箱', 'choices': [{'key': 'gold', 'text': '获得 900 金币'}, {'key': 'reroll', 'text': '获得 1 张刷新券'}]},
  'altar': {'title': '血契祭坛', 'choices': [{'key': 'attack', 'text': '失去 20% 当前生命，获得 80 攻击'}, {'key': 'armor', 'text': '失去 15% 当前生命，获得 45 护甲'}]},
  'relic': {'title': '暗裔遗物', 'choices': [{'key': 'health', 'text': '获得 1200 最大生命'}, {'key': 'relic_attack', 'text': '获得 50 攻击'}]},
}
```

`GET /api/events/<node_id>` must require that `run_map_state.current_node_id == node_id`, `map_nodes.node_type == 'event'`, `state == 'current'`, and the run is active. It uses `INSERT ...` only when no existing record exists and returns `offer`.

- [ ] **Step 4: Register and verify GREEN**

Register `events.bp` in `app/__init__.py`, then run:

`pytest tests/test_events.py::test_current_event_returns_persisted_offer -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/db.py app/__init__.py app/routes/events.py tests/test_events.py
git commit -m "feat: persist random event offers"
```

### Task 2: Apply one-time event choices

**Files:**
- Modify: `app/routes/events.py`
- Modify: `tests/test_events.py`

- [ ] **Step 1: Write failing choice test**

```python
def test_event_choice_closes_node_and_cannot_repeat(client, app):
    node = make_event_current(client, app)
    offer = client.get(f'/api/events/{node}').get_json()['offer']
    choice = offer['choices'][0]['key']
    response = client.post(f'/api/events/{node}/choose', json={'choice_key': choice})
    assert response.status_code == 200
    assert client.post(f'/api/events/{node}/choose', json={'choice_key': choice}).status_code == 409
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_events.py::test_event_choice_closes_node_and_cannot_repeat -q`

Expected: FAIL because the choose endpoint is missing.

- [ ] **Step 3: Implement atomic choice application**

Add `POST /api/events/<node_id>/choose`. In one SQLite connection: load unchosen event, verify `choice_key` is in parsed `choices`, update `node_events.chosen_key`, then apply exactly one result:

```python
if key == 'gold': UPDATE runs SET gold=gold+900
if key == 'reroll': UPDATE runs SET reroll_tokens=reroll_tokens+1
if key == 'attack': UPDATE runs SET hp=max(1, hp-ceil(hp*.20)); INSERT run_stat_shards(..., 'event', 'attack', 80)
if key == 'armor': UPDATE runs SET hp=max(1, hp-ceil(hp*.15)); INSERT run_stat_shards(..., 'event', 'armor', 45)
if key == 'health': INSERT run_stat_shards(..., 'event', 'health', 1200)
if key == 'relic_attack': INSERT run_stat_shards(..., 'event', 'attack', 50)
```

Close the `map_nodes` row, set `runs.stage='event'`, and return `result`, `run`, and `stats`. Do not insert into `run_augments`.

- [ ] **Step 4: Add HP and no-Hex assertions**

```python
def test_altar_keeps_hp_at_least_one_and_never_grants_hex(client, app):
    node = make_event_current(client, app, forced_key='altar', hp=1)
    client.post(f'/api/events/{node}/choose', json={'choice_key': 'attack'})
    assert client.get('/api/state').get_json()['run']['hp'] == 1
    with connect(app) as c:
        assert c.execute('SELECT count(*) FROM run_augments').fetchone()[0] == 0
```

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_events.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routes/events.py tests/test_events.py
git commit -m "feat: resolve one-time event choices"
```

### Task 3: Render event choice cards for players

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing UI contract test**

```python
def test_player_script_renders_random_event_choices(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderRandomEvent' in javascript
    assert b'/api/events/' in javascript
    assert '继续路线'.encode() in javascript
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_ui.py::test_player_script_renders_random_event_choices -q`

Expected: FAIL because no event-node card renderer exists.

- [ ] **Step 3: Implement player event scene**

In `renderApp()`, identify the current map node. When it has `node_type === 'event'` and `state === 'current'`, call `renderRandomEvent()` instead of `renderMapScene()`. It fetches `GET /api/events/<current_node_id>` once, renders its title and `choices` as `.choice-card` buttons, and posts choice keys to `/api/events/<current_node_id>/choose`. After success, append returned `result` to the adventure log, render a completion card, and make its `继续路线` button call `renderMapScene()`.

- [ ] **Step 4: Add event-card styles**

Add `.event-panel`, `.event-result`, `.choice-card.risk`, and `.choice-card.reward`. Mark altar cards as `risk`; all other cards as `reward`. Keep image placeholder slots text-only.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_ui.py::test_player_script_renders_random_event_choices -q && node --check app/static/app.js`

Expected: PASS with no syntax output.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/style.css tests/test_ui.py
git commit -m "feat: render random event cards"
```

### Task 4: Verify end-to-end compatibility

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document node events**

Add a concise player-facing README note that event nodes produce a one-time risk/reward choice and never grant Hexes.

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

Expected: all tests pass, syntax check emits nothing, and the solver prints `flag{docker_test}`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: describe random event nodes"
```
