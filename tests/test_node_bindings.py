def test_entering_shop_node_enables_shop(client, app):
    client.post('/api/runs')
    graph=client.get('/api/map').get_json()['map']
    first=next(edge['to_node_id'] for edge in graph['edges'] if edge['from_node_id']==graph['current_node_id'])
    client.post(f'/api/map/enter/{first}')
    assert client.get('/api/state').get_json()['run']['stage'] == 'hero'


def test_entering_combat_node_returns_updated_run_state(client):
    client.post('/api/runs')
    graph = client.get('/api/map').get_json()['map']
    first = next(edge['to_node_id'] for edge in graph['edges'] if edge['from_node_id'] == graph['current_node_id'])
    response = client.post(f'/api/map/enter/{first}').get_json()
    assert response['run']['stage'] == 'hero'
