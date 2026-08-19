def test_late_floor_elite_is_stronger_than_early_floor_elite():
    from app.content import enemy_for_floor

    assert enemy_for_floor('monster', 20)['hp'] > enemy_for_floor('monster', 5)['hp']
    assert enemy_for_floor('monster', 20)['attack'] > enemy_for_floor('monster', 5)['attack']


def test_floor_reward_increases_by_tier():
    from app.content import enemy_for_floor

    assert enemy_for_floor('minion', 14)['reward'] > enemy_for_floor('minion', 2)['reward']


def test_non_boss_victory_returns_and_adds_floor_gold(client, app, monkeypatch):
    from app.db import connect

    run = client.post('/api/runs').get_json()['run']
    graph = client.get('/api/map').get_json()['map']
    node = next(edge['to_node_id'] for edge in graph['edges'] if edge['from_node_id'] == graph['current_node_id'])
    with connect(app) as c:
        c.execute("UPDATE map_nodes SET node_type='normal' WHERE id=?", (node,))
    client.post(f'/api/map/enter/{node}')
    with connect(app) as c:
        c.execute('UPDATE runs SET enemy_hp=1 WHERE id=?', (run['id'],))
    rolls = iter([0.0, 0.9])
    monkeypatch.setattr('app.routes.game.random.random', lambda: next(rolls))
    response = client.post('/api/game/action', json={'action': 'q'}).get_json()
    assert response['gold_reward'] > 0
    assert response['run']['gold'] == response['gold_reward']
    assert response['enemy_damage'] == 0
    assert response['run']['hp'] == 7000
