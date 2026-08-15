let currentNode = null;
const el = (selector) => document.querySelector(selector);
const call = async (path, body) => {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  el('#log').textContent = JSON.stringify(data, null, 2);
  render(data);
  return data;
};
const refreshMap = async () => {
  const data = await call('/api/map');
  if (!data.map) return;
  currentNode = data.map.current_node_id;
  const reachable = new Set(data.map.edges.filter((edge) => edge.from_node_id === currentNode).map((edge) => edge.to_node_id));
  el('#map').innerHTML = data.map.nodes.map((node) => `<button class="node ${node.state}" data-node="${node.id}" ${reachable.has(node.id) ? '' : 'disabled'}>${node.floor}F ${node.node_type}</button>`).join('');
  document.querySelectorAll('[data-node]').forEach((button) => { button.onclick = async () => { await call(`/api/map/enter/${button.dataset.node}`, {}); refreshMap(); }; });
};
function render(data) {
  if (!data.run) return;
  const stats = data.stats || {};
  el('#state').textContent = `关卡：${data.run.stage} ｜ 金币：${data.run.gold} ｜ HP：${data.run.hp}/${stats.max_hp} ｜ 攻击：${stats.attack} ｜ 护甲：${stats.armor} ｜ 蒙多 HP：${data.run.boss_hp}`;
  if (data.flag) el('#state').innerHTML += `<div class="flag">${data.flag}</div>`;
}
function showOffers(offer) {
  el('#offers').innerHTML = (offer || []).map((hex) => `<button data-hex="${hex.id}">${hex.name}<small>${hex.description}</small></button>`).join('');
  document.querySelectorAll('[data-hex]').forEach((button) => { button.onclick = () => call(`/api/campfires/${currentNode}/meditate/choose`, {augment_id: button.dataset.hex}); });
}
el('#start').onclick = async () => { await call('/api/runs', {}); refreshMap(); };
document.querySelectorAll('[data-action]').forEach((button) => { button.onclick = () => call('/api/game/action', {action: button.dataset.action}); });
el('#claim').onclick = () => call('/api/rewards/hero/claim', {});
el('#buy').onclick = () => call('/api/shop/batch-buy', {item_ids: JSON.parse(el('#batch').value)});
el('#anvil').onclick = () => call('/api/shop/anvils', {});
el('#rest').onclick = () => call(`/api/campfires/${currentNode}/rest`, {});
el('#meditate').onclick = async () => showOffers((await call(`/api/campfires/${currentNode}/meditate`, {})).offer);
el('#reroll').onclick = async () => showOffers((await call(`/api/campfires/${currentNode}/meditate/reroll`, {})).offer);
el('#search').onclick = async () => showOffers((await call(`/api/campfires/${currentNode}/meditate/search?q=${encodeURIComponent(el('#query').value)}`)).results);
