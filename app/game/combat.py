from math import floor
def armor_damage(raw, armor): return floor(raw*100/(100+armor))
def q_raw(stage, attack): return {1:200+1.5*attack,2:350+2.2*attack,3:600+4*attack}[stage]
def advance_q(stage): return 1 if stage==3 else stage+1
def boss_q3_damage(attack, boss_armor, boss_max_hp, has_contract):
    raw=q_raw(3,attack)
    if has_contract: raw=raw*7.5+boss_max_hp*.35
    return armor_damage(raw,boss_armor)
