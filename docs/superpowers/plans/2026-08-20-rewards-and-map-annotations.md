# 海克斯奖励与地图标记 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让海克斯数值生效、英雄节点奖励可领取，并提供本局持久的地图手绘标记。

**Architecture:** 后端通过海克斯效果表统一累加角色属性，掷骰狂人的即时资源直接写入 run 状态。英雄奖励记录改为每个节点独立的 key，但保留读取记录与写入记录之间的竞态窗口。前端在地图渲染容器中加入本地存储驱动的 Canvas 覆盖层，只有标记模式接收绘制输入。

**Tech Stack:** Flask、SQLite、Vanilla JavaScript、Canvas 2D、localStorage、pytest。

---

### Task 1: 海克斯属性和掷骰狂人即时奖励

**Files:**
- Modify: `app/content.py`
- Modify: `app/models.py`
- Modify: `app/routes/campfires.py`
- Modify: `app/db.py`
- Modify: `tests/test_campfires.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_chosen_stat_augment_changes_stats(client, app):
    run = client.post('/api/runs').get_json()['run']
    node = make_campfire_current(app, run['id'])
    with client.session_transaction() as session:
        session['campfire_node'] = node
        session['campfire_ids'] = ['dragon']
    response = client.post(f'/api/campfires/{node}/meditate/choose', json={'augment_id': 'dragon'})
    assert response.get_json()['stats']['attack'] == 410


def test_gamba_adds_rerolls_and_three_free_anvils(client, app):
    run = client.post('/api/runs').get_json()['run']
    node = make_campfire_current(app, run['id'])
    with client.session_transaction() as session:
        session['campfire_node'] = node
        session['campfire_ids'] = ['gamba']
    response = client.post(f'/api/campfires/{node}/meditate/choose', json={'augment_id': 'gamba'}).get_json()
    assert response['run']['reroll_tokens'] == 3
    assert response['run']['free_anvils'] == 3
```

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_campfires.py::test_chosen_stat_augment_changes_stats tests/test_campfires.py::test_gamba_adds_rerolls_and_three_free_anvils -q`

Expected: FAIL，因为 `stats()` 尚未读取 `run_augments`，且 `runs` 没有 `free_anvils`。

- [ ] **Step 3: 实现数据与结算**

在 `app/content.py` 定义 `AUGMENT_STAT_BONUSES = {'soul': ('health', 800), 'dragon': ('attack', 60), 'goliath': ('health', 1200), 'ika': ('armor', 35), 'basics': ('attack', 30), 'slap': ('attack', 15), 'tooth': ('health', 600), 'escape': ('armor', 10)}`。在 `runs` 表增加 `free_anvils INTEGER NOT NULL DEFAULT 0`，并在 `stats()` 查询 `run_augments` 后合并上述属性。篝火选择成功时，对 `gamba` 将 `reroll_tokens` 加 2、`free_anvils` 加 3；响应包含最新 `run` 与 `stats`。

- [ ] **Step 4: 验证通过**

Run: `pytest tests/test_campfires.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/content.py app/db.py app/models.py app/routes/campfires.py tests/test_campfires.py
git commit -m "feat: apply augment stats and gamba rewards"
```

### Task 2: 商店消费免费锻造资格

**Files:**
- Modify: `app/routes/shop.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_free_anvil_generates_offer_without_spending_gold(client, app):
    run = client.post('/api/runs').get_json()['run']
    set_stage(app, run['id'], 'shop')
    with connect(app) as c:
        c.execute('UPDATE runs SET free_anvils=1 WHERE id=?', (run['id'],))
    response = client.post('/api/shop/anvils').get_json()
    assert response['ok']
    assert response['run']['gold'] == 0
    assert response['run']['free_anvils'] == 0
```

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_core.py::test_free_anvil_generates_offer_without_spending_gold -q`

Expected: FAIL，因为当前锻造器始终要求并扣除 750 金币。

- [ ] **Step 3: 实现免费资格优先扣除**

在 `app/routes/shop.py` 的 `/api/shop/anvils` 中，使用单条条件更新将 `free_anvils` 大于 0 的资格减一；更新成功时跳过金币检查和扣款。否则维持现有 750 金币校验与扣除。响应中返回更新后的 `run`，使前端能够显示次数。

- [ ] **Step 4: 验证通过**

Run: `pytest tests/test_core.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/routes/shop.py tests/test_core.py
git commit -m "feat: spend gamba free anvil charges"
```

### Task 3: 每个英雄节点的战利品结算与竞态保持

**Files:**
- Modify: `app/routes/rewards.py`
- Modify: `app/static/app.js`
- Modify: `tests/test_exploits.py`
- Modify: `tests/test_ui.py`
- Modify: `scripts/solve.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_each_cleared_hero_node_can_be_claimed_once(client, app):
    run = client.post('/api/runs').get_json()['run']
    with connect(app) as c:
        heroes = c.execute("SELECT id FROM map_nodes WHERE run_id=? AND node_type='hero' LIMIT 2", (run['id'],)).fetchall()
        c.executemany("UPDATE map_nodes SET state='cleared' WHERE id=?", [(hero['id'],) for hero in heroes])
    assert client.post('/api/rewards/hero/claim', json={'node_id': heroes[0]['id']}).get_json()['ok']
    assert client.post('/api/rewards/hero/claim', json={'node_id': heroes[1]['id']}).get_json()['ok']


def test_player_script_renders_hero_reward_resolution(client):
    javascript = client.get('/static/app.js').data
    assert b'renderHeroRewardScene' in javascript
    assert b'/api/rewards/hero/claim' in javascript
```

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_exploits.py::test_each_cleared_hero_node_can_be_claimed_once tests/test_ui.py::test_player_script_renders_hero_reward_resolution -q`

Expected: FAIL，因为领取记录是全局 `hero`，且没有英雄胜利结算界面。

- [ ] **Step 3: 实现按节点领取与结算 UI**

在领取接口读取 `node_id`，确认其为该 run 中已清除的英雄节点；令 `reward_key = f'hero:{node_id}'`，并在既有 `time.sleep` 窗口前检查、窗口后发放 1500 金币与 1 张刷新券、再插入该 key。保留未加锁的分段事务。同步将 `tests/test_exploits.py` 与 `scripts/solve.py` 的并发请求都改为发送第一名英雄的 node ID。

在 `app/static/app.js` 中，当战斗结果清除英雄节点时保存 `gameState.heroRewardNode`，渲染 `renderHeroRewardScene()`，展示奖励说明与领取按钮；按钮将 node ID 发给领取接口，成功后清除临时状态并渲染地图。移除商店中的误置“领取英雄战利品”按钮。

- [ ] **Step 4: 验证竞态与界面**

Run: `pytest tests/test_exploits.py tests/test_ui.py -q`

Expected: PASS，包含原有并发领取测试经按节点参数更新后仍可累计多次奖励。

- [ ] **Step 5: 提交**

```bash
git add app/routes/rewards.py app/static/app.js tests/test_exploits.py tests/test_ui.py scripts/solve.py
git commit -m "feat: resolve rewards for each defeated hero"
```

### Task 4: 本局持久地图手绘标记

**Files:**
- Modify: `app/static/app.js`
- Create: `app/static/map-annotations.css`
- Modify: `app/templates/index.html`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_player_script_defines_run_scoped_map_annotations(client):
    javascript = client.get('/static/app.js').data
    assert b'map-annotations:' in javascript
    assert b'annotation-canvas' in javascript
    assert b'localStorage' in javascript
    assert b'annotation-mode' in javascript
```

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_ui.py::test_player_script_defines_run_scoped_map_annotations -q`

Expected: FAIL，因为地图只有 SVG 边与节点，未存储笔迹。

- [ ] **Step 3: 实现 Canvas 标记层**

在 `renderMapScene()` 的 `.map-canvas` 添加同尺寸 `canvas#annotation-canvas`、模式选择按钮与清空按钮。用 `map-annotations:${gameState.run.id}` 作为 localStorage key 保存笔画数组。绘制模式采样 `pointerdown`、`pointermove`、`pointerup` 坐标并重绘；擦除模式以 `destination-out` 绘制；普通模式设置 `pointer-events:none`，使节点保持可点击。新局 run ID 不同即为空白。

- [ ] **Step 4: 添加样式并加载**

在 `app/static/map-annotations.css` 定义绝对定位、与地图同层级的画布、模式按钮与激活状态。通过 `app/templates/index.html` 在主样式之后加载该文件，确保画布展示在边线之上、节点之下。

- [ ] **Step 5: 验证通过**

Run: `pytest tests/test_ui.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add app/static/app.js app/static/map-annotations.css app/templates/index.html tests/test_ui.py
git commit -m "feat: add persistent map annotations"
```

### Task 5: 全量回归与容器验证

**Files:**
- Test: `tests/`
- Test: `scripts/solve.py`

- [ ] **Step 1: 执行全量单元测试**

Run: `pytest -q`

Expected: PASS。

- [ ] **Step 2: 构建并启动容器**

Run: `FLAG='flag{docker_test}' docker compose up --build -d`

Expected: `hks_web-game-1` 状态为 `Up`，端口 `8080` 对外映射。

- [ ] **Step 3: 验证预期利用链**

Run: `python scripts/solve.py`

Expected: 输出 `flag{docker_test}`，证明海克斯/奖励体验修复没有关闭 SQL 注入、竞态或批量购买漏洞。
