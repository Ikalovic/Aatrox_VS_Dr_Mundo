# 战斗独立浮字层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让战斗伤害、受伤和治疗浮字在界面刷新后完整显示 1.6 秒。

**Architecture:** 在页面根部放置一个独立于 `#scene-battle` 的固定特效容器。`showFloatText` 根据当前目标元素的视口位置向该容器追加浮字；战斗场景重绘不再触及该容器。CSS 负责 2.4rem 字号、语义颜色、描边和 1.6 秒上浮淡出。

**Tech Stack:** Vanilla JavaScript、CSS、pytest。

---

### Task 1: 为独立特效层建立前端回归测试

**Files:**
- Modify: `tests/test_ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_player_script_mounts_float_text_outside_battle_scene(client):
    javascript = client.get('/static/app.js').data
    assert b'id="combat-fx-layer"' in javascript
    assert b'getBoundingClientRect' in javascript
    assert b'fxLayer.append(float)' in javascript
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `pytest tests/test_ui.py::test_player_script_mounts_float_text_outside_battle_scene -q`

Expected: FAIL，因为当前脚本将浮字附加到会被 `renderBattleScene` 替换的战斗单位。

- [ ] **Step 3: 实现最小独立挂载逻辑**

在 `app/static/app.js` 的顶部创建一次 `combat-fx-layer` 并挂入 `document.body`；将 `showFloatText` 改为读取目标的 `getBoundingClientRect()`，设置浮字 `left` 与 `top` 后调用 `fxLayer.append(float)`。保留 `animationend` 后移除节点的清理逻辑。

- [ ] **Step 4: 运行测试并确认通过**

Run: `pytest tests/test_ui.py::test_player_script_mounts_float_text_outside_battle_scene -q`

Expected: PASS。

- [ ] **Step 5: 提交测试与逻辑**

```bash
git add app/static/app.js tests/test_ui.py
git commit -m "fix: preserve combat float effects across renders"
```

### Task 2: 提升浮字可读性并验证完整项目

**Files:**
- Modify: `app/static/style.css`
- Test: `tests/test_ui.py`

- [ ] **Step 1: 写入失败测试**

```python
def test_combat_float_effect_has_prominent_readable_duration(client):
    stylesheet = client.get('/static/style.css').data
    assert b'font-size:2.4rem' in stylesheet
    assert b'animation:float-up 1.6s' in stylesheet
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `pytest tests/test_ui.py::test_combat_float_effect_has_prominent_readable_duration -q`

Expected: FAIL，因为当前样式为 `1.7rem` 和 `1s`。

- [ ] **Step 3: 实现可读性样式**

将 `.float-text` 调整为固定定位、`font-size:2.4rem`、`animation:float-up 1.6s ease-out forwards`，并加入 `-webkit-text-stroke` 与 `text-shadow`。保留伤害、受伤、治疗三种颜色。

- [ ] **Step 4: 运行完整测试**

Run: `pytest -q`

Expected: PASS。

- [ ] **Step 5: 提交样式**

```bash
git add app/static/style.css tests/test_ui.py
git commit -m "style: enlarge and extend combat float text"
```
