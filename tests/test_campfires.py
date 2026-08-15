def test_campfire_meditation_offers_three_public_augments(client, app):
    run=client.post('/api/runs').get_json()['run']
    from app.db import connect
    with connect(app) as c:
        node=c.execute("SELECT id FROM map_nodes WHERE run_id=? AND node_type='campfire' LIMIT 1",(run['id'],)).fetchone()['id']
    response=client.post(f'/api/campfires/{node}/meditate')
    assert response.status_code == 200
    assert len(response.get_json()['offer']) == 3
