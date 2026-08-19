---
title: "暗裔远征：剑魔 VS 蒙多"
ctf: "校内 CTF"
date: 2026-08-20
category: web
difficulty: medium
points: 0
flag_format: "flag{...}"
author: "Ikalovic"
---

# 暗裔远征：剑魔 VS 蒙多 Writeup

## Summary

题目要求击败强化后的蒙多。正常篝火无法获得必要的“暗裔契约”，正常装备数量和金币也不足。预期解法串联三处漏洞：篝火搜索 SQL 注入选取隐藏海克斯、英雄战利品的条件竞争刷金币、商店批量购买只按不同装备种类计价而按请求数量入库。

## 环境

```bash
FLAG='flag{test_flag}' docker compose up --build
python3 -m pip install requests
python3 scripts/solve.py http://localhost:8080
```

## 解题步骤

### 1. 并发领取首个英雄节点的战利品

第 2 层固定存在英雄节点。击败后，`POST /api/rewards/hero/claim` 先检查该节点的领取记录，随后存在一个竞争窗口，最后才写入记录。对同一 `node_id` 并发请求会使多个请求都通过检查，并重复获得金币和刷新券。

### 2. 批量购买复制装备

在商店调用：

```json
{"item_ids":["heartsteel", "heartsteel", "bloodmail", "bloodmail"]}
```

后端以去重后的 `item_ids` 计算价格，却遍历原列表逐件插入库存。因此用并发刷出的金币请求大量心之钢、霸王血铠和饮血剑，即可获得远超正常上限的生命、攻击和吸血。

### 3. SQL 注入取得暗裔契约

篝火冥想后的搜索接口将 `q` 直接拼进 `LIKE` 条件。使用以下 payload 联合查询隐藏海克斯：

```text
%' UNION SELECT id,name,rarity,description FROM augments -- 
```

返回的 `darkin-contract` 会写入当前篝火候选，可以照常调用选择接口领取。它令剑魔 Q3 对蒙多获得最大生命伤害和残血斩杀，是跨过蒙多回血阶段的关键。

### 4. 在 Boss 战使用 Q 循环

持续施放 Q，第三段 Q 在暗裔契约、复制装备和矮人杀手增伤下触发斩杀，返回环境变量中的 Flag。

## 完整脚本

完整、可直接运行的解题脚本位于 [scripts/solve.py](scripts/solve.py)。其流程为：进入首个英雄节点并并发领取、在首个商店复制装备、在篝火注入取得暗裔契约、自动结算沿途节点，最后循环 Q 击败蒙多。

```bash
python3 scripts/solve.py http://localhost:8080
```

示例输出：

```text
flag{test_flag}
```

## Flag

```text
flag{test_flag}
```
