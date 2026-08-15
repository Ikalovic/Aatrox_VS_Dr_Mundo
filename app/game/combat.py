from math import floor
def armor_damage(raw, armor): return floor(raw*100/(100+armor))
def accuracy_hit(roll, chance): return roll < chance
def q_raw(stage, attack): return {1:200+1.5*attack,2:350+2.2*attack,3:600+4*attack}[stage]
def advance_q(stage): return 1 if stage==3 else stage+1
def boss_q3_damage(attack, boss_armor, boss_max_hp, has_contract):
    raw=q_raw(3,attack)
    if has_contract: raw=raw*7.5+boss_max_hp*.35
    return armor_damage(raw,boss_armor)

def resolve_turn(state, action, attack, armor, enemy_attack, enemy_armor, rolls):
    state=dict(state); hit_roll,dodge_roll=rolls; state['enemy_raw_attack']=enemy_attack
    apply_w_debuff=state.get('w_debuff_pending',False)
    state['w_debuff_pending']=False
    multiplier=1.25 if state.get('r_turns',0) else 1
    raw=0; hit=True
    if action=='q':
        raw=q_raw(state['q_stage'],attack*multiplier); hit=accuracy_hit(hit_roll,.9); state['q_stage']=advance_q(state['q_stage'])
    elif action=='w':
        raw=250+attack*multiplier; hit=accuracy_hit(hit_roll,.7)
        if hit: state['w_debuff_pending']=True
    elif action=='e': state['e_lifesteal_turns']=3
    elif action=='r': state['r_turns']=3
    dealt=armor_damage(raw,enemy_armor) if hit else 0
    if dealt and state.get('e_lifesteal_turns',0):
        state['hp']+=floor(dealt*.3); state['e_lifesteal_turns']-=1
    raw_enemy=enemy_attack*.8 if apply_w_debuff else enemy_attack
    state['enemy_raw_attack']=int(raw_enemy)
    effective_armor=armor+(100 if action=='e' else 0)
    state['enemy_damage']=0 if dodge_roll<.1 else armor_damage(raw_enemy,effective_armor)
    state['hp']-=state['enemy_damage']; state['damage']=dealt; state['hit']=hit
    if state.get('r_turns',0): state['r_turns']-=1
    return state
