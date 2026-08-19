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


def test_player_script_renders_random_event_choices(client):
    javascript = client.get('/static/app.js').data
    assert b'function renderRandomEvent' in javascript
    assert b'/api/events/' in javascript
    assert '继续路线'.encode() in javascript


def test_player_script_announces_battle_gold_rewards(client):
    javascript = client.get('/static/app.js').data
    assert b'gold_reward' in javascript
    assert '获得 ${data.gold_reward} 金币'.encode() in javascript


def test_player_script_renders_svg_map_edges_and_node_information(client):
    javascript = client.get('/static/app.js').data
    assert b'<svg' in javascript
    assert b'<line' in javascript
    assert b'NODE_INFO' in javascript
    assert '第 ${node.floor} 层'.encode() in javascript


def test_player_script_has_restart_and_combat_float_text(client):
    javascript = client.get('/static/app.js').data
    assert b'async function startNewRun' in javascript
    assert b'function showFloatText' in javascript
    assert b'enemy_max_hp' in javascript


def test_player_script_defines_skill_and_purchase_explanations(client):
    javascript = client.get('/static/app.js').data
    assert b'SKILL_INFO' in javascript
    assert b'PURCHASE_ERRORS' in javascript
    assert '命中率'.encode() in javascript
    assert '金币不足'.encode() in javascript


def test_player_script_uses_compact_skill_cards_and_visible_lifesteal(client):
    javascript = client.get('/static/app.js').data
    assert '吸血 ${stats.lifesteal}%'.encode() in javascript
    assert '三段斩击'.encode() in javascript
    assert '200 + 150%攻击'.encode() in javascript
    assert b'class="skill-tooltip"' in javascript


def test_player_script_mounts_float_text_outside_battle_scene(client):
    javascript = client.get('/static/app.js').data
    assert b'combat-fx-layer' in javascript
    assert b'getBoundingClientRect' in javascript
    assert b'fxLayer.append(float)' in javascript


def test_combat_float_effect_has_prominent_readable_duration(client):
    stylesheet = client.get('/static/combat-effects.css').data
    assert b'font-size: 2.4rem' in stylesheet
    assert b'animation: float-up 1.6s' in stylesheet


def test_player_script_renders_hero_reward_resolution(client):
    javascript = client.get('/static/app.js').data
    assert b'renderHeroRewardScene' in javascript
    assert b'/api/rewards/hero/claim' in javascript
