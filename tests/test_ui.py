def test_root_has_game_shell(client):
    response=client.get("/")
    assert response.status_code == 200
    assert '暗裔远征'.encode() in response.data
    assert b'id="start"' in response.data


def test_root_has_player_scene_shells(client):
    html = client.get('/').data
    assert b'id="topbar"' in html
    assert b'id="scene-map"' in html
    assert b'id="scene-battle"' in html
    assert b'id="scene-event"' in html
    assert b'id="activity-log"' in html
    assert b'id="debug"' not in html


def test_player_shell_uses_scene_renderer_contract(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderMapScene' in javascript
    assert b'function renderTopbar' in javascript
    assert b'current_node_id' in javascript


def test_player_script_defines_battle_scene_with_four_moves(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderBattleScene' in javascript
    for move in (b'Q', b'W', b'E', b'R'):
        assert move in javascript
    assert b'player-tooltip' in javascript


def test_player_script_defines_card_based_event_scenes(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderShopEvent' in javascript
    assert b'function renderCampfireEvent' in javascript
    assert '采购清单'.encode() in javascript
    assert '研究档案'.encode() in javascript
    assert b'function renderAnvilOffer' in javascript


def test_root_does_not_expose_raw_debug_controls(client):
    html = client.get('/').data
    assert b'id="log"' not in html
    assert b'id="boss"' not in html
    assert b'JSON.stringify' not in html
