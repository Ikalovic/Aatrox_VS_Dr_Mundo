def test_new_run_has_seeded_twelve_floor_map(app):
    from app.models import create_run, map_snapshot

    run_id = create_run(app, seed=7)
    graph = map_snapshot(app, run_id)
    assert max(node["floor"] for node in graph["nodes"]) == 12
    assert graph["required_route"] == ["hero", "shop", "campfire", "boss"]
    assert graph['current_node_id'].endswith(':n1_0')


def test_two_runs_have_distinct_persisted_map_node_ids(app):
    from app.models import create_run, map_snapshot

    first = map_snapshot(app, create_run(app, seed=1))
    second = map_snapshot(app, create_run(app, seed=2))
    assert first['current_node_id'] != second['current_node_id']
