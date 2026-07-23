from .models import ElementType, TypeMatchup


def get_multiplier(attacking, defending):
    """获取单属性克制倍率，默认 1.0"""
    matchup = TypeMatchup.objects.filter(
        attacking_type=attacking, defending_type=defending
    ).first()
    return matchup.multiplier if matchup else 1.0


def compute_combined_multipliers(defending_elements):
    """
    双属性加法公式：2.0+2.0=3.0 / 2.0+1.0=2.0 / 2.0+0.5=1.0
                    0.5+1.0=0.5 / 0.5+0.5=0.25
    返回 {attacking_element: multiplier}（仅非 1.0）
    """
    all_elements = ElementType.objects.all()
    result = {}

    for atk in all_elements:
        if len(defending_elements) == 1:
            mult = get_multiplier(atk, defending_elements[0])
        else:
            m1 = get_multiplier(atk, defending_elements[0])
            m2 = get_multiplier(atk, defending_elements[1])
            if m1 > 1.0 and m2 > 1.0:
                mult = m1 + m2 - 1.0    # 双克制：2.0+2.0-1.0=3.0
            else:
                mult = m1 * m2           # 其他情况用乘法

        if mult != 1.0:
            result[atk] = mult

    return result


def compute_type_matchups(defending_elements):
    """按档位分组"""
    combined = compute_combined_multipliers(defending_elements)
    tiers = {3.0: [], 2.0: [], 0.5: [], 0.25: []}
    for elem, mult in combined.items():
        if mult in tiers:
            tiers[mult].append(elem)
    return tiers


def build_evolution_tree(pet):
    """构建进化链树，返回根节点递归结构"""
    from .models import Evolution

    # 找到进化链根节点
    root = pet
    visited = {pet.id}
    while True:
        prev = Evolution.objects.filter(
            pet_to=root
        ).select_related('pet_from').first()
        if prev:
            if prev.pet_from.id in visited:
                break
            root = prev.pet_from
            visited.add(root.id)
        else:
            break

    def build_node(p, visited_nodes=None):
        if visited_nodes is None:
            visited_nodes = set()
        if p.id in visited_nodes:
            return {'pet': p, 'evolutions': []}

        visited_nodes.add(p.id)
        evolutions = Evolution.objects.filter(
            pet_from=p
        ).select_related('pet_to')

        return {
            'pet': p,
            'evolutions': [
                build_node(e.pet_to, visited_nodes.copy())
                for e in evolutions
            ],
        }

    return build_node(root)
