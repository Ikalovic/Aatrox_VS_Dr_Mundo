def test_map_rejects_non_adjacent_node(client):
    client.post('/api/runs')
    graph=client.get('/api/map').get_json()['map']
    target=next(n['id'] for n in graph['nodes'] if n['floor']==4)
    assert client.post(f'/api/map/enter/{target}').status_code == 409
