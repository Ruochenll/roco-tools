"""
洛克王国世界 PVP 伤害计算引擎。

公式来源于社区伤害计算器 (MD/游戏机制/伤害计算器-洛克王国世界 (1).xlsx)。

默认参数：
  星级 = 5, 成长星数 = 0
  强化/弱化层数、特性增益 = 手动指定
"""

import math
from dataclasses import dataclass, field
from typing import Literal


# ── 数据结构 ──

@dataclass
class PetStats:
    """精灵能力值输入。"""
    hp: int = 0             # 种族值（伤害计算用不到 HP 但必填）
    physical_attack: int = 0
    magical_attack: int = 0
    physical_defense: int = 0
    magical_defense: int = 0
    speed: int = 0

    level: int = 60      # 等级，默认 60

    # 天分：6 项属性中选 3 项加点，每项 0-10
    talent_hp: int = 0
    talent_pa: int = 0
    talent_ma: int = 0
    talent_pd: int = 0
    talent_md: int = 0
    talent_sp: int = 0

    # 性格：↑加成 / ↓削弱 / -不变
    nature_hp: Literal['↑', '↓', '-'] = '-'
    nature_pa: Literal['↑', '↓', '-'] = '-'
    nature_ma: Literal['↑', '↓', '-'] = '-'
    nature_pd: Literal['↑', '↓', '-'] = '-'
    nature_md: Literal['↑', '↓', '-'] = '-'
    nature_sp: Literal['↑', '↓', '-'] = '-'

    star: int = 5        # 星级，默认 5
    growth: int = 0      # 成长星数，默认 0


@dataclass
class SkillConfig:
    """技能配置。"""
    power: int           # 技能面板威力
    is_stab: bool = False  # 是否本系加成
    awakening: int = 0     # 觉醒等级（影响本系加成系数）


@dataclass
class BattleContext:
    """战场环境。"""
    ability_boost: float = 0.0      # 特性增益（如 0.2 = 20%）
    atk_boost_stage: int = 0         # 攻击/魔攻强化层数
    def_boost_stage: int = 0         # 防御/魔抗强化层数（对方）
    type_multiplier: float = 1.0     # 克制倍率 (3/2/1/0.5/0.25)
    power_bonus: int = 0             # 威力增加数值（加在技能威力上）
    power_mul: float = 1.0           # 威力加成（乘在威力上）
    combo: int = 1                   # 连击数（最终伤害乘数）


# ── 核心计算 ──

def _round(x: float) -> int:
    """四舍五入 (游戏用ROUND, 非Python银行家舍入)。"""
    return int(x + 0.5) if x >= 0 else int(x - 0.5)

def _calc_stat(base: int, talent: int, nature: str,
               level: int, star: int, growth: int) -> int:
    """
    计算单项能力值（攻击/防御通用）。

    公式：
      base_val = round((base + talent/2*(1+star)) * (level+50)/100 + 10)
      modified = round(base_val * nature_modifier)
      result   = modified + growth + star*10
    """
    base_val = (base + talent / 2 * (1 + star)) * (level + 50) / 100 + 10
    base_val = _round(base_val)

    if nature == '↑':
        nature_mod = 1.1 + 0.02 * star
    elif nature == '↓':
        nature_mod = 0.9
    else:
        nature_mod = 1.0

    modified = _round(base_val * nature_mod)
    return modified + growth + star * 10


def _calc_hp(base: int, talent: int, nature: str,
             level: int, star: int, growth: int) -> int:
    """
    计算生命值。

    公式：
      base_val = round((base + talent/2*(1+star)) * (2*level+50)/100 + level + 10)
      modified = round(base_val * nature_modifier)
      result   = modified + 2*growth + star*20
    """
    base_val = (base + talent / 2 * (1 + star)) * (2 * level + 50) / 100 + level + 10
    base_val = _round(base_val)

    if nature == '↑':
        nature_mod = 1.1 + 0.02 * star
    elif nature == '↓':
        nature_mod = 0.9
    else:
        nature_mod = 1.0

    modified = _round(base_val * nature_mod)
    return modified + 2 * growth + star * 20


def calc_pet_stats(pet: PetStats) -> dict:
    """计算精灵的 6 项最终能力值。"""
    return {
        "hp": _calc_hp(pet.hp, pet.talent_hp, pet.nature_hp,
                       pet.level, pet.star, pet.growth),
        "physical_attack": _calc_stat(pet.physical_attack, pet.talent_pa,
                                      pet.nature_pa, pet.level, pet.star, pet.growth),
        "magical_attack": _calc_stat(pet.magical_attack, pet.talent_ma,
                                     pet.nature_ma, pet.level, pet.star, pet.growth),
        "physical_defense": _calc_stat(pet.physical_defense, pet.talent_pd,
                                       pet.nature_pd, pet.level, pet.star, pet.growth),
        "magical_defense": _calc_stat(pet.magical_defense, pet.talent_md,
                                      pet.nature_md, pet.level, pet.star, pet.growth),
        "speed": _calc_stat(pet.speed, pet.talent_sp,
                           pet.nature_sp, pet.level, pet.star, pet.growth),
    }


def calc_effective_power(skill_power: int, ctx: BattleContext,
                         skill: SkillConfig | None = None) -> float:
    """
    计算技能实际威力。

    公式（不含强化层数——强化已移至面板值阶段）：
      power = (技能面板威力 + 威力增加数值) × 本系加成 × 威力加成 × 克制倍率
    """
    stab = 1.0
    if skill and skill.is_stab:
        stab = 1.25 + 0.15 * skill.awakening

    return ((skill_power + ctx.power_bonus) *
            (1 + ctx.ability_boost) *
            stab *
            ctx.power_mul *
            ctx.type_multiplier)


def calc_damage(atk_stat: int, effective_power: float, def_stat: int,
                atk_boost: int = 0, def_boost: int = 0, combo: int = 1) -> int:
    """
    计算最终伤害。

    公式：
      atk_eff = 攻击力 × (1 + 0.1 × 攻强)
      def_eff = 防御力 × (1 + 0.1 × 防强)
      damage  = INT( ROUND(atk_eff × 有效威力 × 37/41, 0) / def_eff ) × 连击数
    """
    atk_eff = atk_stat * (1 + 0.1 * atk_boost)
    def_eff = def_stat * (1 + 0.1 * def_boost)
    base_dmg = int(_round(atk_eff * effective_power * 37 / 41) / def_eff)
    return base_dmg * combo


# ── 便捷接口 ──

def quick_damage(
    attacker_stats: PetStats,
    defender_stats: PetStats,
    skill: SkillConfig,
    ctx: BattleContext,
    use_physical: bool = True,
) -> int:
    """
    一键伤害计算：根据攻防双方配置，返回最终伤害值。

    Args:
        attacker_stats: 进攻方精灵配置
        defender_stats: 防守方精灵配置
        skill: 技能配置
        ctx: 战场环境（特性、强化层数、克制倍率）
        use_physical: True=物攻, False=魔攻
    """
    atk_pet = calc_pet_stats(attacker_stats)
    def_pet = calc_pet_stats(defender_stats)

    atk_val = atk_pet["physical_attack"] if use_physical else atk_pet["magical_attack"]
    def_val = (def_pet["physical_defense"] if use_physical
               else def_pet["magical_defense"])

    power = calc_effective_power(skill.power, ctx, skill)
    return calc_damage(atk_val, power, def_val,
                       atk_boost=ctx.atk_boost_stage,
                       def_boost=ctx.def_boost_stage,
                       combo=ctx.combo)


# ── 测试 ──

if __name__ == "__main__":
    # 用 xlsx 中的样例数据验证
    # C3=120(物攻种族), D3=10(天分), F3=60(等级), G3=0(成长), H3=5(星), E3=- (性格不变)
    # → C14=225 (理论攻击力)
    # 防守: C4=87(物防种族), D4=0(天分) → C15=156 (理论防御力)
    # 技能威力=80, 本系加成: 是(1.25), 3倍克制 → C16=300 (理论威力)
    # 理论伤害: F16=INT(ROUND(225*300*37/41)/156)=390

    attacker = PetStats(
        physical_attack=120, talent_pa=10,
        level=60, star=5, growth=0,
    )
    defender = PetStats(
        physical_defense=87, talent_pd=0,
        level=60, star=5, growth=0,
    )
    skill = SkillConfig(power=80, is_stab=True, awakening=0)
    ctx = BattleContext(
        ability_boost=0.0,
        atk_boost_stage=0,
        def_boost_stage=0,
        type_multiplier=3.0,
    )

    # 验证中间值
    atk_stats = calc_pet_stats(attacker)
    def_stats = calc_pet_stats(defender)
    print(f"理论攻击力: {atk_stats['physical_attack']}  (预期 225)")
    print(f"理论防御力: {def_stats['physical_defense']}  (预期 156)")

    power = calc_effective_power(skill.power, ctx, skill)
    print(f"理论威力:   {power:.0f}  (预期 300)")

    dmg = quick_damage(attacker, defender, skill, ctx, use_physical=True)
    print(f"理论伤害:   {dmg}  (预期 390)")
    print(f"验证通过:   {'YES' if dmg == 390 else 'NO'}")
