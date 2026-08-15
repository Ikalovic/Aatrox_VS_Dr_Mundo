const gameState = {run: null, stats: null, map: null, logs: [], campfireOffer: null, anvilOffer: null};
const el = (selector) => document.querySelector(selector);
const NODE_LABELS = {start: '起点', normal: '小兵', elite: '精英', hero: '英雄', shop: '商店', campfire: '篝火', event: '事件', boss: '蒙多'};
const ENEMY_VIEW = {minion: ['小兵', 250], monster: ['野怪', 800], hero: ['敌方英雄', 1800], boss: ['蒙多', 32000]};

function escapeHtml(value) { return String(value).replace(/[&<>"]/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[char])); }
function addLog(text) { gameState.logs.unshift(text); gameState.logs = gameState.logs.slice(0, 8); el('#log-lines').innerHTML = gameState.logs.map((line) => `<li>${escapeHtml(line)}</li>`).join(''); }
function applyResponse(data) { if (data.run) gameState.run = data.run; if (data.stats) gameState.stats = data.stats; renderApp(); return data; }
async function api(path, body) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  const data = await response.json();
  if (!data.ok) addLog(data.error === 'node_not_cleared' ? '当前节点尚未完成。' : `操作失败：${data.error || '未知原因'}`);
  return applyResponse(data);
}
async function refreshMap() { const data = await api('/api/map'); if (data.map) gameState.map = data.map; return data; }
function showScene(name) { ['map', 'battle', 'event'].forEach((scene) => { el(`#scene-${scene}`).hidden = scene !== name; }); }
function renderTopbar() {
  const run = gameState.run; const stats = gameState.stats;
  if (!run || !stats) { el('#run-stats').innerHTML = '<span class="stat-pill">尚未出征</span>'; return; }
  el('#run-stats').innerHTML = `<span class="stat-pill gold">金币 ${run.gold}</span><span class="stat-pill hp">HP ${run.hp}/${stats.max_hp}</span><span class="stat-pill">攻击 ${stats.attack}</span><span class="stat-pill">护甲 ${stats.armor}</span><span class="stat-pill">刷新券 ${run.reroll_tokens}</span>`;
}
function renderMapScene() {
  const map = gameState.map;
  if (!map) return;
  showScene('map');
  const current = map.current_node_id;
  const reachable = new Set(map.edges.filter((edge) => edge.from_node_id === current).map((edge) => edge.to_node_id));
  const floors = map.nodes.reduce((out, node) => { (out[node.floor] ||= []).push(node); return out; }, {});
  el('#scene-map').innerHTML = `<div class="scene-heading"><p class="eyebrow">远征路线</p><h1>选择下一步</h1><p>只有相邻的下一层节点可以进入。</p></div><div class="map-path">${Object.entries(floors).map(([floor, nodes]) => `<div class="map-floor"><span>${floor}F</span><div>${nodes.map((node) => `<button class="map-node ${node.state} ${reachable.has(node.id) ? 'reachable' : ''}" data-node="${node.id}" ${reachable.has(node.id) ? '' : 'disabled'}>${NODE_LABELS[node.node_type]}</button>`).join('')}</div></div>`).join('')}</div>`;
  document.querySelectorAll('[data-node]').forEach((button) => { button.onclick = async () => { const data = await api(`/api/map/enter/${button.dataset.node}`, {}); if (data.ok) { addLog(`进入：${NODE_LABELS[(gameState.map.nodes.find((node) => node.id === button.dataset.node) || {}).node_type] || '未知节点'}`); await refreshMap(); renderApp(); } }; });
}
function renderApp() {
  renderTopbar();
  if (!gameState.run) return;
  if (['minion', 'monster', 'hero', 'boss'].includes(gameState.run.stage)) return renderBattleScene();
  const currentNode = gameState.map && gameState.map.nodes.find((node) => node.id === gameState.map.current_node_id);
  if (gameState.run.stage === 'campfire' && currentNode && currentNode.state === 'closed') return renderMapScene();
  if (['shop', 'campfire'].includes(gameState.run.stage)) return renderEventScene();
  renderMapScene();
}
function healthBar(current, maximum, className = '') { return `<div class="health-bar ${className}"><span style="width:${Math.max(0, Math.min(100, current / maximum * 100))}%"></span></div>`; }
function openModal(title, text, buttonText, action) { el('#modal-root').innerHTML = `<div class="modal-backdrop"><section class="modal"><p class="eyebrow">远征结果</p><h1>${title}</h1><p>${escapeHtml(text)}</p><button id="modal-action" class="primary-action">${buttonText}</button></section></div>`; el('#modal-action').onclick = action; }
function renderBattleScene() {
  showScene('battle');
  const run = gameState.run; const stats = gameState.stats; const [enemyName, enemyMax] = ENEMY_VIEW[run.stage];
  const enemyHp = run.stage === 'boss' ? run.boss_hp : run.enemy_hp;
  const moves = [['q', 'Q', '暗裔利刃', '90% 命中 · 连续三段，第三段最强'], ['w', 'W', '恶火束链', '70% 命中 · 下一次敌方攻击降低 20%'], ['e', 'E', '暗影冲决', '抵挡本回合伤害，并获得吸血'], ['r', 'R', '大灭', '持续 3 回合，攻击力提升 25%']];
  el('#scene-battle').innerHTML = `<div class="battle-top">${healthBar(run.hp, stats.max_hp, 'player')}<span>VS</span>${healthBar(enemyHp, enemyMax, 'enemy')}</div><div class="battle-arena"><article class="combatant player-tooltip" tabindex="0"><div class="portrait-placeholder">剑魔肖像待补充</div><h2>剑魔</h2><p>HP ${run.hp}/${stats.max_hp}</p><div class="tooltip">攻击 ${stats.attack} · 护甲 ${stats.armor} · 闪避 10%</div></article><p class="turn-label">选择招式<br><small>敌方招式将在结算后揭示</small></p><article class="combatant enemy" tabindex="0"><div class="portrait-placeholder">敌方肖像待补充</div><h2>${enemyName}</h2><p>HP ${enemyHp}/${enemyMax}</p><div class="tooltip">护甲 ${run.stage === 'boss' ? 200 : '未知'} · 攻击将在结算后显示</div></article></div><div class="move-grid">${moves.map(([id, key, name, detail]) => `<button class="move-card move-${id}" data-move="${id}"><b>${key}</b><span>${name}</span><small>${detail}</small></button>`).join('')}</div>`;
  document.querySelectorAll('[data-move]').forEach((button) => { button.onclick = async () => {
    const data = await api('/api/game/action', {action: button.dataset.move});
    if (data.ok) addLog(`${button.dataset.move.toUpperCase()}${data.hit ? '命中' : '落空'}，造成 ${data.damage} 伤害${data.enemy_damage ? `；受到 ${data.enemy_damage} 伤害` : '。'}`);
    await refreshMap();
    if (data.flag) return openModal('蒙多倒下了', data.flag, '再开一局', () => { el('#modal-root').innerHTML = ''; el('#start').click(); });
    if (gameState.run.status === 'failed') return openModal('远征失败', '剑魔倒下了，必须重新开始本局。', '重新开始', () => { el('#modal-root').innerHTML = ''; el('#start').click(); });
    renderApp();
  }; });
}
const SHOP_ITEMS = [
  ['heartsteel', '心之钢', 3300, '+40 攻击 · +3000 生命'],
  ['bloodmail', '霸王血铠', 3200, '+100 攻击 · +2500 生命'],
  ['bloodthirster', '饮血剑', 3400, '+90 攻击 · 吸血'],
  ['warmog', '狂徒铠甲', 3100, '+4000 生命'],
];
function renderShopEvent() {
  el('#scene-event').innerHTML = `<div class="scene-heading"><p class="eyebrow">商店</p><h1>选择你的装备</h1><p>金币：${gameState.run.gold}</p></div><div class="choice-grid">${SHOP_ITEMS.map(([id, name, price, detail]) => `<article class="choice-card item-card"><div class="portrait-placeholder">装备图标待补充</div><h2>${name}</h2><p>${detail}</p><button data-buy="${id}"><span class="gold-cost">${price} 金币</span> 购买</button></article>`).join('')}<article class="choice-card"><h2>属性锻造器</h2><p>随机获得攻击、生命或护甲强化。</p><button id="buy-anvil"><span class="gold-cost">750 金币</span> 锻造</button></article></div>${renderAnvilOffer()}<div class="event-footer"><button id="claim-loot">领取英雄战利品</button><button id="leave-event">继续路线</button><details class="details-panel"><summary>采购清单</summary><p>输入以逗号分隔的装备 ID。</p><input id="batch-list" placeholder="heartsteel,bloodmail"><button id="batch-buy">提交清单</button></details></div>`;
  document.querySelectorAll('[data-buy]').forEach((button) => { button.onclick = async () => { const data = await api('/api/shop/buy', {item_id: button.dataset.buy}); if (data.ok) { addLog('购买成功。'); renderShopEvent(); } }; });
  el('#buy-anvil').onclick = async () => { const data = await api('/api/shop/anvils', {}); if (data.ok) { gameState.anvilOffer = data.offer; addLog(`锻造器出现：${data.offer.tier} 品质。`); renderShopEvent(); } };
  el('#claim-loot').onclick = async () => { const data = await api('/api/rewards/hero/claim', {}); if (data.ok) { addLog('英雄战利品已到账。'); renderShopEvent(); } };
  el('#leave-event').onclick = () => renderMapScene();
  el('#batch-buy').onclick = async () => { const ids = el('#batch-list').value.split(',').map((id) => id.trim()).filter(Boolean); const data = await api('/api/shop/batch-buy', {item_ids: ids}); if (data.ok) { addLog('采购清单已结算。'); renderShopEvent(); } };
  document.querySelectorAll('[data-anvil]').forEach((button) => { button.onclick = async () => { const data = await api('/api/shop/anvils/choose', {stat_key: button.dataset.anvil}); if (data.ok) { gameState.anvilOffer = null; addLog('属性强化已完成。'); renderShopEvent(); } }; });
}
function renderAnvilOffer() { if (!gameState.anvilOffer) return ''; const labels = {attack: '攻击', health: '生命', armor: '护甲'}; return `<section class="event-panel"><p class="eyebrow">${gameState.anvilOffer.tier} 锻造结果</p><h2>选择一项属性</h2><div class="choice-grid">${Object.entries(gameState.anvilOffer.options).map(([key, amount]) => `<button class="choice-card" data-anvil="${key}"><h2>${labels[key]} +${amount}</h2><p>立即获得该强化</p></button>`).join('')}</div></section>`; }
function renderCampfireEvent() {
  const offers = gameState.campfireOffer;
  const base = `<div class="scene-heading"><p class="eyebrow">篝火</p><h1>${offers ? '冥想中的低语' : '短暂安歇'}</h1><p>${offers ? '从候选海克斯中选择一项力量。' : '你可以回复生命，或进入冥想。'}</p></div>`;
  const cards = offers ? `<div class="choice-grid">${offers.map((hex) => `<article class="choice-card hex-card ${hex.rarity}"><div class="portrait-placeholder">海克斯图标待补充</div><p class="eyebrow">${hex.rarity}</p><h2>${hex.name}</h2><p>${hex.description}</p><button data-hex="${hex.id}">选择海克斯</button></article>`).join('')}</div><div class="event-footer"><button id="reroll-hex">消耗刷新券刷新</button><details class="details-panel"><summary>研究档案</summary><input id="hex-query" placeholder="输入关键字"><button id="search-hex">检索</button></details></div>` : `<div class="choice-grid"><button id="rest" class="choice-card"><h2>休息</h2><p>回复全部生命值</p></button><button id="meditate" class="choice-card"><h2>冥想</h2><p>发现三项海克斯力量</p></button></div>`;
  el('#scene-event').innerHTML = base + cards;
  if (!offers) { el('#rest').onclick = () => campfireAction('/rest'); el('#meditate').onclick = () => campfireAction('/meditate'); return; }
  document.querySelectorAll('[data-hex]').forEach((button) => { button.onclick = () => campfireAction('/meditate/choose', {augment_id: button.dataset.hex}); });
  el('#reroll-hex').onclick = () => campfireAction('/meditate/reroll');
  el('#search-hex').onclick = () => campfireSearch(el('#hex-query').value);
}
async function campfireAction(suffix, body = {}) { const node = gameState.map.current_node_id; const data = await api(`/api/campfires/${node}${suffix}`, body); if (data.ok && data.offer) gameState.campfireOffer = data.offer; if (data.ok && suffix.includes('choose')) gameState.campfireOffer = null; await refreshMap(); renderApp(); }
async function campfireSearch(query) { const node = gameState.map.current_node_id; const data = await api(`/api/campfires/${node}/meditate/search?q=${encodeURIComponent(query)}`); if (data.ok) { gameState.campfireOffer = data.results; renderCampfireEvent(); } }
function renderEventScene() { showScene('event'); if (gameState.run.stage === 'shop') renderShopEvent(); else renderCampfireEvent(); }
el('#start').onclick = async () => { const data = await api('/api/runs', {}); if (data.ok) { addLog('远征开始。'); await refreshMap(); renderApp(); } };
