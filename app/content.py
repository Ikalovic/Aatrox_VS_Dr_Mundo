ITEMS = {
    "heartsteel": ("心之钢", 3300, 40, 3000, 0, "none", "core-health"),
    "bloodmail": ("霸王血铠", 3200, 100, 2500, 0, "bloodmail", "core-bloodmail"),
    "bloodthirster": ("饮血剑", 3400, 90, 0, 0, "lifesteal_20", "bloodthirster"),
    "warmog": ("狂徒铠甲", 3100, 0, 4000, 0, "heal_full", "core-health"),
}
AUGMENTS = [
    ("darkin-contract", "暗裔契约", "prismatic", "Q3 获得最大生命伤害与斩杀", 1, 1, "darkin_contract"),
    ("gamba", "掷骰狂人", "prismatic", "刷新券+2", 0, 120000000, "reroll"),
    ("soul", "吞噬灵魂", "gold", "最大生命+800", 0, 120000000, "health"),
    ("dragon", "全能龙魂", "prismatic", "攻击+60", 0, 120000000, "attack"),
    ("goliath", "歌利亚巨人", "prismatic", "最大生命+1200", 0, 120000000, "health"),
    ("ika", "艾卡西亚的陷落", "prismatic", "护甲+35", 0, 120000000, "armor"),
    ("basics", "回归基本功", "gold", "攻击+30", 0, 100000000, "attack"),
    ("slap", "扇巴掌", "silver", "攻击+15", 0, 100000000, "attack"),
    ("tooth", "牙仙子", "silver", "最大生命+600", 0, 100000000, "health"),
    ("escape", "逃跑计划", "silver", "护甲+10", 0, 99999999, "armor"),
]
ENEMIES = {
    "minion": ("小兵", 250, 30, 0, 1000, "monster"),
    "monster": ("野怪", 800, 120, 30, 2000, "hero"),
    "hero": ("敌方英雄", 1800, 250, 60, 0, "shop"),
}
ANVIL = {"silver": (80, {"attack": 15, "health": 600, "armor": 10}), "gold": (19, {"attack": 30, "health": 1200, "armor": 20}), "prismatic": (1, {"attack": 60, "health": 2400, "armor": 35})}
