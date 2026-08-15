def make_event_current(client, app):
    from app.db import connect

    run = client.post('/api/runs').get_json()['run']
    with connect(app) as c:
        node = c.execute(
            "SELECT id FROM map_nodes WHERE run_id=? AND node_type='event' LIMIT 1",
            (run['id'],),
        ).fetchone()['id']
        current = c.execute(
            'SELECT current_node_id FROM run_map_state WHERE run_id=?', (run['id'],)
        ).fetchone()['current_node_id']
        c.execute("UPDATE map_nodes SET state='left' WHERE id=?", (current,))
        c.execute("UPDATE map_nodes SET state='current' WHERE id=?", (node,))
        c.execute('UPDATE run_map_state SET current_node_id=? WHERE run_id=?', (node, run['id']))
        c.execute("UPDATE runs SET stage='event' WHERE id=?", (run['id'],))
    return node


def test_current_event_returns_persisted_offer(client, app):
    node = make_event_current(client, app)
    first = client.get(f'/api/events/{node}').get_json()['offer']
    second = client.get(f'/api/events/{node}').get_json()['offer']
    assert first == second
    assert first['event_key'] in {'loot', 'altar', 'relic'}


def test_event_choice_closes_node_and_cannot_repeat(client, app):
    node = make_event_current(client, app)
    offer = client.get(f'/api/events/{node}').get_json()['offer']
    choice = offer['choices'][0]['key']
    response = client.post(f'/api/events/{node}/choose', json={'choice_key': choice})
    assert response.status_code == 200
    assert client.post(f'/api/events/{node}/choose', json={'choice_key': choice}).status_code == 409


def test_altar_keeps_hp_at_least_one_and_never_grants_hex(client, app):
    import json
    from app.db import connect

    node = make_event_current(client, app)
    with connect(app) as c:
        run_id = c.execute('SELECT run_id FROM map_nodes WHERE id=?', (node,)).fetchone()['run_id']
        offer = {'event_key': 'altar', 'title': '血契祭坛', 'choices': [{'key': 'attack', 'text': '失去生命'}]}
        c.execute('UPDATE runs SET hp=1 WHERE id=?', (run_id,))
        c.execute('INSERT INTO node_events(run_id,node_id,event_key,offer_json) VALUES (?,?,?,?)', (run_id, node, 'altar', json.dumps(offer)))
    assert client.post(f'/api/events/{node}/choose', json={'choice_key': 'attack'}).status_code == 200
    assert client.get('/api/state').get_json()['run']['hp'] == 1
    with connect(app) as c:
        assert c.execute('SELECT count(*) FROM run_augments').fetchone()[0] == 0
