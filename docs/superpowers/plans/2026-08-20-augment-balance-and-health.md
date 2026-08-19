# 海克斯平衡与生命同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让生命加成同步治疗，按确认的价值层级重做海克斯，并让掷骰狂人的免费锻造可见可用。

**Architecture:** 将海克斯数值与战斗型效果集中为内容表；在战斗结算读取增伤、吸血与减攻效果。用模型层 `grant_health` 统一更新当前生命，所有生命来源调用它。前端展示免费锻造次数与实时海克斯效果。

**Tech Stack:** Flask、SQLite、Vanilla JavaScript、pytest。

---

### Task 1: 统一生命加成与当前生命

**Files:**
- Modify: `app/models.py`
- Modify: `app/routes/campfires.py`
- Modify: `app/routes/shop.py`
- Modify: `app/routes/events.py`
- Test: `tests/test_campfires.py`
- Test: `tests/test_core.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_health_augment_increases_current_health(client, app):
    run = client.post('/api/runs').get_json()['run']
    node = make_campfire_current(app, run['id'])
    with client.session_transaction() as session:
        session['campfire_node'] = node; session['campfire_ids'] = ['tooth']
    body = client.post(f'/api/campfires/{node}/meditate/choose', json={'augment_id': 'tooth'}).get_json()
    assert body['run']['hp'] == 8200
    assert body['stats']['max_hp'] == 8200
```

- [ ] **Step 2: 验证失败**

Run: `pytest tests/test_campfires.py::test_health_augment_increases_current_health -q`

Expected: FAIL，因为当前只提高 `max_hp`。

- [ ] **Step 3: 实现统一函数并接入来源**

在 `app/models.py` 添加 `grant_health(app, run_id, amount)`：读取 `runs.hp`，计算增加后的 `stats(app, run_id)['max_hp']`，写入 `min(old_hp + amount, max_hp)`，返回 run。海克斯选择在写入 `run_augments` 后调用它；健康装备购买/批量购买、健康锻造选择、遗物 health 选择在写入来源后调用同一函数。

- [ ] **Step 4: 验证全部生命来源**

Run: `pytest tests/test_campfires.py tests/test_core.py tests/test_events.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/models.py app/routes/campfires.py app/routes/shop.py app/routes/events.py tests/test_campfires.py tests/test_core.py tests/test_events.py
git commit -m "fix: heal current health when max health increases"
```

### Task 2: 重做公共海克斯与战斗结算

**Files:**
- Modify: `app/content.py`
- Modify: `app/models.py`
- Modify: `app/game/combat.py`
- Modify: `app/routes/game.py`
- Test: `tests/test_pokemon_combat.py`
- Test: `tests/test_campfires.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_giant_slayer_scales_to_seventy_percent_at_health_threshold():
    assert giant_slayer_multiplier(12000, 10000) == 1.70
    assert giant_slayer_multiplier(6000, 10000) == 1.35


def test_soul_siphon_adds_twenty_five_percent_lifesteal():
    state = resolve_turn({'q_stage': 1, 'hp': 1000}, 'q', 350, 80, 0, 0, [0, .9], lifesteal=25, max_hp=7000)
    assert state['healing'] == int(state['damage'] * .25)
```

- [ ] **Step 2: 验证失败**

Run: `pytest tests/test_pokemon_combat.py::test_giant_slayer_scales_to_seventy_percent_at_health_threshold -q`

Expected: FAIL，因为尚未定义巨人杀手增伤函数。

- [ ] **Step 3: 实现内容与机制**

把公共海克斯替换为确认的数值：银色 60 攻击/1200 生命/30 护甲；金色 25% 吸血、65 护甲、2200 生命及巨人杀手；棱彩 140 攻击、4000 生命、双刀流和掷骰狂人。添加 `giant_slayer_multiplier(enemy_hp, player_max_hp)`，当 `enemy_hp / player_max_hp` 从 0 到 1.2 线性映射为 1 到 1.7，超过 1.2 固定 1.7。将灵魂虹吸吸血、巨人杀手增伤与双刀流下一次敌方攻击 -20% 叠加到现有战斗状态；暗裔契约逻辑不改。

- [ ] **Step 4: 验证战斗与海克斯测试**

Run: `pytest tests/test_pokemon_combat.py tests/test_campfires.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/content.py app/models.py app/game/combat.py app/routes/game.py tests/test_pokemon_combat.py tests/test_campfires.py
git commit -m "feat: rebalance augments and combat effects"
```

### Task 3: 显示并消费掷骰狂人免费锻造

**Files:**
- Modify: `app/static/app.js`
- Modify: `tests/test_ui.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_player_script_shows_free_anvil_charges(client):
    javascript = client.get('/static/app.js').data
    assert b'free_anvils' in javascript
    assert '免费锻造（剩余'.encode() in javascript
```

- [ ] **Step 2: 验证失败**

Run: `pytest tests/test_ui.py::test_player_script_shows_free_anvil_charges -q`

Expected: FAIL，因为当前商店固定显示 750 金币。

- [ ] **Step 3: 实现清晰 UI**

在顶栏加入免费锻造次数；在商店将锻造按钮文案改为 `免费锻造（剩余 ${run.free_anvils}）` 或 `750 金币锻造`。掷骰狂人选择响应在前端日志中显示“获得 2 张刷新券与 3 次免费锻造”。

- [ ] **Step 4: 验证通过**

Run: `pytest tests/test_ui.py tests/test_core.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/static/app.js tests/test_ui.py
git commit -m "feat: show gamba free anvil charges"
```

### Task 4: 全量验证与部署

- [ ] **Step 1: 执行测试**

Run: `pytest -q`

Expected: PASS。

- [ ] **Step 2: 重建并验证容器利用链**

Run: `FLAG='flag{docker_test}' docker compose up --build -d && python scripts/solve.py`

Expected: 容器运行且输出 `flag{docker_test}`。
