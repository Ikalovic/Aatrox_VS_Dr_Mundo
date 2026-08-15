from app.game.combat import accuracy_hit, resolve_turn


def test_accuracy_boundaries():
    assert accuracy_hit(0.89, 0.90)
    assert not accuracy_hit(0.90, 0.90)


def test_w_debuffs_one_enemy_attack():
    state = resolve_turn({"q_stage": 1, "hp": 7000, "w_debuff_pending": False, "e_lifesteal_turns": 0, "r_turns": 0}, "w", 350, 80, 5000, 200, [0.1, 0.9])
    assert state["w_debuff_pending"]
    state = resolve_turn(state, "e", 350, 80, 5000, 200, [0.1, 0.9])
    assert state["enemy_raw_attack"] == 4000
