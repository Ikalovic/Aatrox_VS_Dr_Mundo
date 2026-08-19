import random

NODE_TYPES = ['normal', 'elite', 'event', 'campfire', 'shop', 'hero']
ANCHORS = {2: 'hero', 8: 'hero', 14: 'shop', 20: 'campfire', 25: 'boss'}


def row_width(floor, rng):
    if floor in {1, 25}: return 1
    if floor <= 7: return 2
    if floor <= 17: return 3
    return rng.randint(3, 4)


def generate_map(seed):
    rng = random.Random(seed); nodes = []; edges = []; rows = []
    for floor in range(1, 26):
        row = []
        for column in range(row_width(floor, rng)):
            kind = 'start' if floor == 1 else ('boss' if floor == 25 else rng.choice(NODE_TYPES))
            if floor in ANCHORS and column == 0: kind = ANCHORS[floor]
            node = f'n{floor}_{column}'
            nodes.append({'id': node, 'floor': floor, 'node_type': kind}); row.append(node)
        rows.append(row)
    for left, right in zip(rows, rows[1:]):
        pair_edges = set()
        if len(right) == 1:
            edges.append((left[0], right[0]))
            continue
        for index, source in enumerate(left):
            target_index = min(index, len(right) - 1)
            pair_edges.add((source, right[target_index]))
            neighbors = [candidate for candidate in (target_index - 1, target_index + 1) if 0 <= candidate < len(right)]
            if neighbors and rng.random() < .35 and len(pair_edges) < len(left) * len(right) - 1:
                pair_edges.add((source, right[rng.choice(neighbors)]))
        for target_index, target in enumerate(right):
            if not any(edge[1] == target for edge in pair_edges):
                source = left[min(target_index, len(left) - 1)]
                if len(pair_edges) < len(left) * len(right) - 1: pair_edges.add((source, target))
        edges.extend(sorted(pair_edges))
    return nodes, edges
