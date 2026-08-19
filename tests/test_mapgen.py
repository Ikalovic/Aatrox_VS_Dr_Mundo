def test_new_run_has_seeded_twenty_five_floor_map(app):
    from app.models import create_run, map_snapshot

    run_id = create_run(app, seed=7)
    graph = map_snapshot(app, run_id)
    assert max(node["floor"] for node in graph["nodes"]) == 25
    assert graph["required_route"] == ["hero", "shop", "campfire", "boss"]
    assert graph['current_node_id'].endswith(':n1_0')


def test_generated_map_has_variable_row_widths_and_no_full_adjacent_connections():
    from app.game.mapgen import generate_map

    nodes, edges = generate_map(11)
    rows = {floor: [node['id'] for node in nodes if node['floor'] == floor] for floor in range(1, 26)}
    assert len(rows[1]) == len(rows[25]) == 1
    assert all(4 <= len(rows[floor]) <= 6 for floor in range(2, 25))
    for floor in range(2, 25):
        between = [(left, right) for left, right in edges if left in rows[floor] and right in rows[floor + 1]]
        assert len(between) < len(rows[floor]) * len(rows[floor + 1])


def test_two_runs_have_distinct_persisted_map_node_ids(app):
    from app.models import create_run, map_snapshot

    first = map_snapshot(app, create_run(app, seed=1))
    second = map_snapshot(app, create_run(app, seed=2))
    assert first['current_node_id'] != second['current_node_id']
