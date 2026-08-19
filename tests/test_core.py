from app.game.combat import armor_damage, advance_q, boss_q3_damage
from app.models import create_run, get_run, set_gold, set_stage, stats


def test_combat_contract_values():
    assert armor_damage(5000, 80) == 2777
    assert [advance_q(1), advance_q(2), advance_q(3)] == [2, 3, 1]
    assert boss_q3_damage(1490, 200, 32000, True) == 20133


def test_new_run_and_duplicate_batch_purchase(client, app):
    run_id = create_run(app)
    assert get_run(app, run_id)["gold"] == 0
    set_gold(app, run_id, 6500)
    set_stage(app, run_id, "shop")
    with client.session_transaction() as session:
        session["run_id"] = run_id
    response = client.post("/api/shop/batch-buy", json={"item_ids": ["heartsteel"] * 4 + ["bloodmail"] * 4})
    assert response.status_code == 200
    assert stats(app, run_id) == {"attack": 1490, "max_hp": 29000, "armor": 80, "lifesteal": 0}


def test_bloodthirster_stacks_visible_lifesteal(app):
    from app.db import connect
    run_id = create_run(app)
    with connect(app) as c:
        c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)", (run_id, 'bloodthirster'))
        c.execute("INSERT INTO inventory(run_id,item_id) VALUES (?,?)", (run_id, 'bloodthirster'))
    assert stats(app, run_id)['lifesteal'] == 40


def test_free_anvil_generates_offer_without_spending_gold(client, app):
    from app.db import connect
    run = client.post('/api/runs').get_json()['run']
    set_stage(app, run['id'], 'shop')
    with connect(app) as c:
        c.execute('UPDATE runs SET free_anvils=1 WHERE id=?', (run['id'],))
    response = client.post('/api/shop/anvils').get_json()
    assert response['ok']
    assert response['run']['gold'] == 0
    assert response['run']['free_anvils'] == 0
