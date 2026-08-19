def test_entering_combat_writes_actual_enemy_max_hp(client, app):
    from app.db import connect

    client.post('/api/runs')
    graph = client.get('/api/map').get_json()['map']
    node = next(edge['to_node_id'] for edge in graph['edges'] if edge['from_node_id'] == graph['current_node_id'])
    with connect(app) as c:
        c.execute("UPDATE map_nodes SET node_type='normal' WHERE id=?", (node,))
    client.post(f'/api/map/enter/{node}')
    run = client.get('/api/state').get_json()['run']
    assert run['enemy_hp'] == run['enemy_max_hp']
    assert run['enemy_max_hp'] > 0
