ITEMS = {
    "heartsteel": ("心之钢", 3300, 40, 3000, 0, "none", "core-health"),
    "bloodmail": ("霸王血铠", 3200, 100, 2500, 0, "bloodmail", "core-bloodmail"),
    "bloodthirster": ("饮血剑", 3400, 90, 0, 0, "lifesteal_20", "bloodthirster"),
    "warmog": ("狂徒铠甲", 3100, 0, 4000, 0, "heal_full", "core-health"),
}
AUGMENTS = [
    ("darkin-contract", "暗裔契约", "prismatic", "Q3 获得最大生命伤害与斩杀", 1, 1, "darkin_contract"),
    ("gamba", "掷骰狂人", "prismatic", "刷新券+2，获得3次免费锻造", 0, 120000000, "reroll"),
    ("soul", "灵魂虹吸", "gold", "吸血+25%", 0, 120000000, "lifesteal"),
    ("giant-slayer", "巨人杀手", "gold", "敌方生命越高，伤害最高+70%", 0, 120000000, "giant_slayer"),
    ("steel", "钢化你心", "gold", "最大生命+2200", 0, 120000000, "health"),
    ("dragon", "全能龙魂", "prismatic", "攻击+140", 0, 120000000, "attack"),
    ("goliath", "歌利亚巨人", "prismatic", "最大生命+4000", 0, 120000000, "health"),
    ("dual-wield", "双刀流", "prismatic", "攻击+100；Q/W命中后敌方下次攻击-20%", 0, 120000000, "dual_wield"),
    ("ika", "艾卡西亚的陷落", "gold", "护甲+65", 0, 120000000, "armor"),
    ("basics", "回归基本功", "silver", "攻击+60", 0, 100000000, "attack"),
    ("tooth", "牙仙子", "silver", "最大生命+1200", 0, 100000000, "health"),
    ("escape", "逃跑计划", "silver", "护甲+30", 0, 99999999, "armor"),
]
AUGMENT_STAT_BONUSES = {
    "steel": ("health", 2200), "dragon": ("attack", 140), "goliath": ("health", 4000),
    "dual-wield": ("attack", 100), "ika": ("armor", 65), "basics": ("attack", 60),
    "tooth": ("health", 1200), "escape": ("armor", 30),
}
ENEMIES = {
    "minion": ("小兵", 250, 30, 0, 1000, "monster"),
    "monster": ("野怪", 800, 120, 30, 2000, "hero"),
    "hero": ("敌方英雄", 1800, 250, 60, 0, "shop"),
}
ENEMY_FLOOR_BASES = {
    "minion": (900, 420, 25, 700, 250, 260, 110, 15),
    "monster": (1600, 720, 60, 1400, 400, 420, 170, 20),
    "hero": (3600, 1050, 95, 3000, 700, 650, 240, 25),
}
PRESSURE_MULTIPLIERS = {"minion": (1.25, 1.30), "monster": (1.35, 1.35), "hero": (1.45, 1.40)}

def enemy_for_floor(enemy_key, floor):
    hp, attack, armor, reward, reward_step, hp_step, attack_step, armor_step = ENEMY_FLOOR_BASES[enemy_key]
    tier = floor // 6
    hp += hp_step * tier; attack += attack_step * tier; armor += armor_step * tier; reward += reward_step * tier
    if 17 <= floor <= 24:
        hp_multiplier, attack_multiplier = PRESSURE_MULTIPLIERS[enemy_key]
        hp = int(hp * hp_multiplier); attack = int(attack * attack_multiplier)
    return {"hp": int(hp), "attack": int(attack), "armor": int(armor), "reward": int(reward)}
ANVIL = {"silver": (80, {"attack": 15, "health": 600, "armor": 10}), "gold": (19, {"attack": 30, "health": 1200, "armor": 20}), "prismatic": (1, {"attack": 60, "health": 2400, "armor": 35})}
