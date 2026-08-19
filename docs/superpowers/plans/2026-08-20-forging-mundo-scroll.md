# 无限锻造、蒙多与滚动恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取消锻造次数限制、强化蒙多、以矮人杀手替代巨人杀手，并保持页面滚动位置。

**Architecture:** 内容表保存下调的锻造数值；商店只检查待选项和金币/免费次数。战斗按 Boss 阶段常量与矮人杀手生命比结算。前端在每次场景替换前后读取和恢复滚动位置。

**Tech Stack:** Flask、SQLite、Vanilla JavaScript、pytest。

---

### Task 1: 无限低收益锻造

**Files:** `app/content.py`, `app/routes/shop.py`, `tests/test_core.py`

- [ ] 写失败测试：向同一 run 插入三条锻造碎片后，750 金币锻造仍成功。
- [ ] 运行 `pytest tests/test_core.py -q`，确认当前 `anvil_limit_reached` 失败。
- [ ] 将 `ANVIL` 设为银色 8/300/5、金色 16/600/10、棱彩 32/1200/18；移除 `used>=3` 分支，保留待选项、免费次数与金币检查。
- [ ] 运行 `pytest tests/test_core.py -q`，提交 `feat: allow unlimited low-yield forging`。

### Task 2: 矮人杀手与强化蒙多

**Files:** `app/content.py`, `app/game/combat.py`, `app/routes/game.py`, `tests/test_pokemon_combat.py`, `tests/test_exploits.py`

- [ ] 写失败测试：`dwarf_slayer_multiplier(32000,10000)==1.7`，`dwarf_slayer_multiplier(10000,10000)==1`。
- [ ] 运行目标测试，确认函数不存在。
- [ ] 用矮人杀手替换巨人杀手；按 `(player_max_hp/enemy_max_hp-1)/(3.2-1)*.7` 截断到 0–.7；蒙多设为 48000/6500/240，40% 以下每回合回复 21600、10000 攻击、300 护甲；暗裔契约 Q3 使用 48000 最大生命与 19200 斩杀阈值。
- [ ] 运行战斗和利用测试，提交 `feat: strengthen mundo and add dwarf slayer`。

### Task 3: 场景滚动恢复

**Files:** `app/static/app.js`, `tests/test_ui.py`

- [ ] 写失败测试：脚本含 `scrollPositions`、`saveScrollPosition`、`restoreScrollPosition`。
- [ ] 运行 `pytest tests/test_ui.py -q`，确认失败。
- [ ] 在 `showScene` 切换前保存可见场景的 `window.scrollY`，渲染完成后以 `requestAnimationFrame` 恢复当前场景值；地图、商店、战斗分别使用键名。
- [ ] 运行 UI 测试，提交 `fix: preserve scene scroll positions`。

### Task 4: 验证

- [ ] 运行 `pytest -q`。
- [ ] 运行 `FLAG='flag{docker_test}' docker compose up --build -d && python scripts/solve.py`。
