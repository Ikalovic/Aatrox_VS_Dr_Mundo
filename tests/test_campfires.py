def make_campfire_current(app, run_id):
    from app.db import connect
    with connect(app) as c:
        node = c.execute(
            "SELECT id FROM map_nodes WHERE run_id=? AND node_type='campfire' LIMIT 1",
            (run_id,),
        ).fetchone()['id']
        current = c.execute(
            "SELECT current_node_id FROM run_map_state WHERE run_id=?", (run_id,)
        ).fetchone()['current_node_id']
        c.execute("UPDATE map_nodes SET state='left' WHERE id=?", (current,))
        c.execute("UPDATE map_nodes SET state='current' WHERE id=?", (node,))
        c.execute("UPDATE run_map_state SET current_node_id=? WHERE run_id=?", (node, run_id))
    return node


def test_campfire_meditation_offers_three_public_augments(client, app):
    run=client.post('/api/runs').get_json()['run']
    node = make_campfire_current(app, run['id'])
    response=client.post(f'/api/campfires/{node}/meditate')
    assert response.status_code == 200
    assert len(response.get_json()['offer']) == 3


def test_campfire_must_be_the_current_map_node(client, app):
    run = client.post('/api/runs').get_json()['run']
    from app.db import connect

    with connect(app) as c:
        node = c.execute(
            "SELECT id FROM map_nodes WHERE run_id=? AND node_type='campfire' LIMIT 1",
            (run['id'],),
        ).fetchone()['id']

    response = client.post(f'/api/campfires/{node}/rest')
    assert response.status_code == 409
    assert response.get_json()['error'] == 'invalid_campfire'


def test_meditation_reroll_costs_token_and_replaces_candidates(client, app):
    run = client.post('/api/runs').get_json()['run']
    node = make_campfire_current(app, run['id'])
    first = client.post(f'/api/campfires/{node}/meditate').get_json()['offer']
    response = client.post(f'/api/campfires/{node}/meditate/reroll')
    assert response.status_code == 200
    assert len(response.get_json()['offer']) == 3
    assert client.get('/api/state').get_json()['run']['reroll_tokens'] == 0
    assert all('id' in candidate for candidate in first)


def test_global_augment_endpoints_are_not_hex_source(client):
    client.post('/api/runs')
    assert client.get('/api/augments/search').status_code == 404
