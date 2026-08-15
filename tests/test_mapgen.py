def test_new_run_has_seeded_twelve_floor_map(app):
    from app.models import create_run, map_snapshot

    run_id = create_run(app, seed=7)
    graph = map_snapshot(app, run_id)
    assert max(node["floor"] for node in graph["nodes"]) == 12
    assert graph["required_route"] == ["hero", "shop", "campfire", "boss"]
    assert graph['current_node_id'] == 'n1_0'
