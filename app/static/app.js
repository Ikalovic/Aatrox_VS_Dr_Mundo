const gameState = {run: null, stats: null, map: null, logs: [], campfireOffer: null, anvilOffer: null, randomEvent: null, randomEventNode: null, randomEventResult: null, eventLoading: false};
const el = (selector) => document.querySelector(selector);
const NODE_LABELS = {start: '起点', normal: '小兵', elite: '精英', hero: '英雄', shop: '商店', campfire: '篝火', event: '事件', boss: '蒙多'};
const ENEMY_VIEW = {minion: ['小兵', 250], monster: ['野怪', 800], hero: ['敌方英雄', 1800], boss: ['蒙多', 32000]};
const NODE_INFO = {start: ['起点', '整备', '开始远征'], normal: ['小兵', '低风险', '获得金币'], elite: ['精英', '高风险', '更多金币'], hero: ['英雄', '高风险', '英雄战利品'], shop: ['商店', '休整', '购买装备'], campfire: ['篝火', '休整', '回复或冥想'], event: ['事件', '未知', '风险或收益'], boss: ['蒙多', '终局', '击败以获得 Flag']};
const SKILL_INFO = {
  q: {name: '暗裔利刃', tag: '90%命中 · 三段斩击', detail: '亚托克斯挥动巨剑发动三段斩击。每段有 90% 命中率，依次造成 200 + 150%攻击、350 + 220%攻击、600 + 400%攻击 原始伤害；伤害受敌方护甲减免。第三段最强。持有“暗裔契约”时，Q3 额外获得强化、最大生命伤害与残血斩杀。'},
  w: {name: '恶火束链', tag: '70%命中 · 减攻', detail: '亚托克斯投出恶火束链。命中率 70%，造成 250 + 100%攻击 原始伤害；命中后敌人的下一次攻击降低 20%。'},
  e: {name: '暗影冲决', tag: '护甲+100 · 吸血', detail: '亚托克斯获得本回合 100 护甲。随后三回合，造成伤害时额外获得 30% 吸血；可与装备吸血叠加。'},
  r: {name: '大灭', tag: '攻击+25% · 3回合', detail: '亚托克斯开启大灭，持续三回合攻击力提升 25%。'}
};
const PURCHASE_ERRORS = {invalid_purchase: '金币不足、背包已满或装备规则冲突。请检查金币与已装备物品。', stage_locked: '此处无法购买。请先进入商店节点。', invalid_id: '该物品不存在。请重新选择。'};

function escapeHtml(value) { return String(value).replace(/[&<>"]/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[char])); }
function addLog(text) { gameState.logs.unshift(text); gameState.logs = gameState.logs.slice(0, 8); el('#log-lines').innerHTML = gameState.logs.map((line) => `<li>${escapeHtml(line)}</li>`).join(''); }
function applyResponse(data) { if (data.run) gameState.run = data.run; if (data.stats) gameState.stats = data.stats; renderApp(); return data; }
async function api(path, body) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  const data = await response.json();
  if (!data.ok) { const message = PURCHASE_ERRORS[data.error] || (data.error === 'node_not_cleared' ? '当前节点尚未完成。' : '操作暂时无法完成。'); addLog(message); if (path.startsWith('/api/shop')) openModal('无法完成购买', message, '知道了', () => { el('#modal-root').innerHTML = ''; }); }
  return applyResponse(data);
}
async function refreshMap() { const data = await api('/api/map'); if (data.map) gameState.map = data.map; return data; }
function showScene(name) { ['map', 'battle', 'event'].forEach((scene) => { el(`#scene-${scene}`).hidden = scene !== name; }); }
function renderTopbar() {
  const run = gameState.run; const stats = gameState.stats;
  if (!run || !stats) { el('#run-stats').innerHTML = '<span class="stat-pill">尚未出征</span>'; return; }
  el('#run-stats').innerHTML = `<span class="stat-pill gold">金币 ${run.gold}</span><span class="stat-pill hp">HP ${run.hp}/${stats.max_hp}</span><span class="stat-pill">攻击 ${stats.attack}</span><span class="stat-pill">护甲 ${stats.armor}</span><span class="stat-pill">吸血 ${stats.lifesteal}%</span><span class="stat-pill">刷新券 ${run.reroll_tokens}</span>`;
}
function renderMapScene() {
  const map = gameState.map;
  if (!map) return;
  showScene('map');
  const current = map.current_node_id;
  const reachable = new Set(map.edges.filter((edge) => edge.from_node_id === current).map((edge) => edge.to_node_id));
  const floors = map.nodes.reduce((out, node) => { (out[node.floor] ||= []).push(node); return out; }, {}); const width = 760; const height = Math.max(600, Object.keys(floors).length * 104 + 70);
  const positions = {}; Object.entries(floors).forEach(([floor, nodes]) => nodes.forEach((node, index) => { positions[node.id] = {x: Math.round(width * (index + 1) / (nodes.length + 1)), y: 48 + (Number(floor) - 1) * 104}; }));
  const lines = map.edges.map((edge) => { const from = positions[edge.from_node_id], to = positions[edge.to_node_id]; const source = map.nodes.find((node) => node.id === edge.from_node_id); return `<line class="map-line ${edge.from_node_id === current ? 'route-active' : (source && ['left', 'cleared'].includes(source.state) ? 'route-cleared' : '')}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"/>`; }).join('');
  const buttons = map.nodes.map((node) => { const [title, risk, reward] = NODE_INFO[node.node_type]; const point = positions[node.id]; return `<button class="map-node-dot ${node.node_type} ${node.state} ${reachable.has(node.id) ? 'reachable' : ''}" data-node="${node.id}" style="left:${point.x}px;top:${point.y}px" ${reachable.has(node.id) ? '' : 'disabled'} aria-label="第 ${node.floor} 层 ${title}，${risk}，${reward}"><b>${node.floor}</b><span>${title}</span><i class="node-tooltip">第 ${node.floor} 层 · ${title}<br>${risk} · ${reward}</i></button>`; }).join('');
  el('#scene-map').innerHTML = `<div class="scene-heading"><p class="eyebrow">远征路线</p><h1>选择下一步</h1><p>发光连线表示当前可走路线；悬停节点可查看风险与收益。</p></div><div class="map-viewport"><div class="map-canvas" style="width:${width}px;height:${height}px"><svg class="map-lines" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">${lines}</svg>${buttons}</div></div>`;
  document.querySelectorAll('[data-node]').forEach((button) => { button.onclick = async () => { const data = await api(`/api/map/enter/${button.dataset.node}`, {}); if (data.ok) { addLog(`进入：${NODE_LABELS[(gameState.map.nodes.find((node) => node.id === button.dataset.node) || {}).node_type] || '未知节点'}`); await refreshMap(); renderApp(); } }; });
}
function renderApp() {
  renderTopbar();
  if (!gameState.run) return;
  if (['minion', 'monster', 'hero', 'boss'].includes(gameState.run.stage)) return renderBattleScene();
  const currentNode = gameState.map && gameState.map.nodes.find((node) => node.id === gameState.map.current_node_id);
  if (currentNode && currentNode.node_type === 'event' && (currentNode.state === 'current' || gameState.randomEventResult)) return renderRandomEvent();
  if (gameState.run.stage === 'campfire' && currentNode && currentNode.state === 'closed') return renderMapScene();
  if (['shop', 'campfire'].includes(gameState.run.stage)) return renderEventScene();
  renderMapScene();
}
function healthBar(current, maximum, className = '') { return `<div class="health-bar ${className}"><span style="width:${Math.max(0, Math.min(100, current / maximum * 100))}%"></span></div>`; }
function showFloatText(selector, text, kind) { const target = el(selector); if (!target) return; const float = document.createElement('span'); float.className = `float-text ${kind}`; float.textContent = text; target.append(float); float.addEventListener('animationend', () => float.remove()); }
function openModal(title, text, buttonText, action) { el('#modal-root').innerHTML = `<div class="modal-backdrop"><section class="modal"><p class="eyebrow">远征结果</p><h1>${title}</h1><p>${escapeHtml(text)}</p><button id="modal-action" class="primary-action">${buttonText}</button></section></div>`; el('#modal-action').onclick = action; }
function renderBattleScene() {
  showScene('battle');
  const run = gameState.run; const stats = gameState.stats; const [enemyName, staticMax] = ENEMY_VIEW[run.stage]; const enemyMax = run.stage === 'boss' ? staticMax : run.enemy_max_hp;
  const enemyHp = run.stage === 'boss' ? run.boss_hp : run.enemy_hp;
  const moves = [['q', 'Q'], ['w', 'W'], ['e', 'E'], ['r', 'R']];
  el('#scene-battle').innerHTML = `<div class="battle-top">${healthBar(run.hp, stats.max_hp, 'player')}<span>VS</span>${healthBar(enemyHp, enemyMax, 'enemy')}</div><div class="battle-arena"><article class="combatant player-tooltip" tabindex="0"><div class="portrait-placeholder">剑魔肖像待补充</div><h2>剑魔</h2><p>HP ${run.hp}/${stats.max_hp}</p><div class="tooltip">攻击 ${stats.attack} · 护甲 ${stats.armor} · 吸血 ${stats.lifesteal}% · 闪避 10%</div></article><p class="turn-label">选择招式<br><small>敌方招式将在结算后揭示</small></p><article class="combatant enemy" tabindex="0"><div class="portrait-placeholder">敌方肖像待补充</div><h2>${enemyName}</h2><p>HP ${enemyHp}/${enemyMax}</p><div class="tooltip">护甲 ${run.stage === 'boss' ? 200 : '未知'} · 攻击将在结算后显示</div></article></div><div class="move-grid">${moves.map(([id, key]) => `<button class="move-card move-${id}" data-move="${id}"><b>${key}</b><span>${SKILL_INFO[id].name}</span><small>${SKILL_INFO[id].tag}</small><i class="skill-tooltip">${SKILL_INFO[id].detail}</i></button>`).join('')}</div>`;
  document.querySelectorAll('[data-move]').forEach((button) => { button.onclick = async () => {
    const data = await api('/api/game/action', {action: button.dataset.move});
    if (data.ok) { addLog(`${button.dataset.move.toUpperCase()}${data.hit ? '命中' : '落空'}，造成 ${data.damage} 伤害${data.enemy_damage ? `；受到 ${data.enemy_damage} 伤害` : '。'}`); if (data.gold_reward > 0) addLog(`胜利！获得 ${data.gold_reward} 金币。`); }
    if (data.ok && data.damage) showFloatText('.combatant.enemy', `-${data.damage}`, 'damage');
    if (data.ok && data.enemy_damage) showFloatText('.combatant.player-tooltip', `-${data.enemy_damage}`, 'damage-taken');
    if (data.ok && data.healing > 0) showFloatText('.combatant.player-tooltip', `+${data.healing}`, 'heal');
    await refreshMap();
    if (data.flag) return openModal('蒙多倒下了', data.flag, '再开一局', () => { el('#modal-root').innerHTML = ''; startNewRun(); });
    if (gameState.run.status === 'failed') return openModal('远征失败', '剑魔倒下了，必须重新开始本局。', '重新开始', () => { el('#modal-root').innerHTML = ''; startNewRun(); });
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
async function loadRandomEvent() {
  if (gameState.eventLoading || !gameState.map) return;
  gameState.eventLoading = true;
  const node = gameState.map.current_node_id;
  const response = await fetch(`/api/events/${node}`); const data = await response.json();
  gameState.eventLoading = false;
  if (data.ok) { gameState.randomEvent = data.offer; gameState.randomEventNode = node; renderRandomEvent(); }
  else { addLog(`事件加载失败：${data.error || '未知原因'}`); renderMapScene(); }
}
function renderRandomEvent() {
  showScene('event');
  const node = gameState.map.current_node_id;
  if (gameState.randomEventResult) { el('#scene-event').innerHTML = `<section class="event-panel event-result"><p class="eyebrow">事件结算</p><h1>${escapeHtml(gameState.randomEventResult)}</h1><button id="continue-route" class="primary-action">继续路线</button></section>`; el('#continue-route').onclick = () => { gameState.randomEventResult = null; gameState.randomEvent = null; renderMapScene(); }; return; }
  if (!gameState.randomEvent || gameState.randomEventNode !== node) { el('#scene-event').innerHTML = '<section class="event-panel"><p>事件正在展开……</p></section>'; loadRandomEvent(); return; }
  const offer = gameState.randomEvent; const risk = offer.event_key === 'altar';
  el('#scene-event').innerHTML = `<section class="event-panel"><p class="eyebrow">随机事件</p><h1>${escapeHtml(offer.title)}</h1><p>${risk ? '力量总是伴随着代价。' : '你发现了一份可以带走的收获。'}</p><div class="choice-grid">${offer.choices.map((choice) => `<button class="choice-card ${risk ? 'risk' : 'reward'}" data-event-choice="${choice.key}"><div class="portrait-placeholder">事件插画待补充</div><h2>${escapeHtml(choice.text)}</h2><p>选择后不可撤销</p></button>`).join('')}</div></section>`;
  document.querySelectorAll('[data-event-choice]').forEach((button) => { button.onclick = async () => { const data = await api(`/api/events/${node}/choose`, {choice_key: button.dataset.eventChoice}); if (!data.ok) return; gameState.randomEventResult = data.result; addLog(data.result); await refreshMap(); renderApp(); }; });
}
async function startNewRun() { gameState.map = null; gameState.campfireOffer = null; gameState.anvilOffer = null; gameState.randomEvent = null; gameState.randomEventResult = null; const data = await api('/api/runs', {}); if (data.ok) { gameState.logs = ['远征开始。']; await refreshMap(); renderApp(); } }
el('#start').onclick = startNewRun;
