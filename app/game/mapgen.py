import random

def generate_map(seed):
    rng=random.Random(seed); nodes=[]; edges=[]; floors=[]
    forced={2:'hero',5:'shop',8:'campfire',12:'boss'}
    choices=['normal','elite','event','campfire','shop','hero']
    for floor in range(1,13):
        count=1 if floor in (1,12) else 2
        row=[]
        for column in range(count):
            kind='start' if floor==1 else forced.get(floor, rng.choice(choices))
            if column and floor not in forced: kind=rng.choice(choices)
            node=f'n{floor}_{column}'; nodes.append({'id':node,'floor':floor,'node_type':kind}); row.append(node)
        floors.append(row)
    for left,right in zip(floors,floors[1:]):
        for src in left:
            for dst in right: edges.append((src,dst))
    return nodes,edges
