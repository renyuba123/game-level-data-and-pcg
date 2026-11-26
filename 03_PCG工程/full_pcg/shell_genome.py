"""Explicit shell partitions and local edits in the Phase 2 generation family."""
from copy import deepcopy

import networkx as nx
from shapely.geometry import Polygon
from shapely.ops import unary_union

from full_pcg.common import ROOT, digest, read
from full_pcg.godot_export import package
from full_pcg.shell_layout import attempt, build, certify_navigation, corner_room


SIBLINGS = (('left_inner','left_low'), ('east_high','east_low'))


def graph(layout):
    result = nx.Graph()
    result.add_nodes_from(room['id'] for room in layout['rooms'])
    result.add_edges_from((p['a'],p['b']) for p in layout['portals'])
    return result


def polygons(partitions):
    return {name:Polygon(coords) for name,coords in partitions}


def serialize(cells):
    return [[id,[list(point) for point in poly.exterior.coords]] for id,poly in cells.items()]


def initial(seed):
    source = build(seed)
    return dict(schema='shell-pilot-genome/1', seed=seed, door_attempt=source['door_attempt'],
                repair_reasons=source['repair_reasons'], partitions=[[r['id'],r['polygon']] for r in source['rooms']],
                edited_partition=False,
                closed_pairs=[], opening_shifts=[])


def realize(genome):
    if genome['schema'] != 'shell-pilot-genome/1':
        raise ValueError('unknown_shell_genome_version')
    ids = [name for name,_ in genome['partitions']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_partition_ids')
    layout = attempt(genome['seed'],genome['door_attempt'],
                     partition=genome['partitions'] if genome['edited_partition'] else None,
                     closed_pairs={tuple(pair) for pair in genome['closed_pairs']},
                     opening_shifts={tuple(pair):value for pair,value in genome['opening_shifts']})
    if not genome['edited_partition']:
        original = [[room['id'],room['polygon']] for room in layout['rooms']]
        if digest(original)!=digest(genome['partitions']):
            raise ValueError('base_partition_identity_changed')
    if len(layout['supplies'])!=6:
        raise ValueError('fixed_supply_count')
    layout['repair_reasons'] = genome['repair_reasons']
    layout.pop('layout_hash')
    layout['layout_hash'] = digest(layout)
    packet = package(layout,read(ROOT/'configs/full_pcg_v2.json'))
    certify_navigation(layout,packet)
    return packet


def proposals(parent, layout):
    cells = polygons(parent['partitions'])
    actions = []
    for host, pocket in SIBLINGS:
        if host not in cells:
            continue
        if pocket in cells:
            actions.extend([('merge',host,pocket), ('move_partition',host,pocket)])
        else:
            actions.append(('split',host,pocket))
    actual = graph(layout)
    bridges = {tuple(sorted(edge)) for edge in nx.bridges(actual)}
    pairs = {tuple(sorted(edge)) for edge in actual.edges}
    for a,b in sorted(pairs):
        # Do not modify a hall seam or the sole shared wall of a terminal room.
        if {a,b} & {'hall','foyer'}:
            continue
        actions.append(('shift_opening',a,b))
        if (a,b) not in bridges and min(actual.degree[a],actual.degree[b])>=3:
            actions.append(('seal_connection',a,b))
    actions.extend(('restore_connection',*pair) for pair in parent['closed_pairs'])
    return actions


def apply_edit(parent, action, rng, *, preferred_corner=None):
    kind,a,b = action
    child = deepcopy(parent)
    if kind in ('merge','split','move_partition'):
        cells = polygons(parent['partitions'])
        base = unary_union([cells[a], cells[b]]) if b in cells else cells[a]
        if base.geom_type != 'Polygon' or base.interiors:
            raise ValueError('unsupported_parent_partition')
        if kind == 'merge':
            cells[a] = cells[a].union(cells.pop(b))
            child['closed_pairs'] = [pair for pair in child['closed_pairs'] if b not in pair]
            child['opening_shifts'] = [row for row in child['opening_shifts'] if b not in row[0]]
        else:
            result = corner_room(base,a,b,rng,preferred_corner=preferred_corner)
            if result is None:
                raise ValueError('no_legal_corner_partition')
            cells[a],cells[b] = result
        child['partitions'] = serialize(cells)
        child['edited_partition'] = True
    elif kind in ('seal_connection','restore_connection'):
        closed = {tuple(pair) for pair in child['closed_pairs']}
        pair = tuple(sorted((a,b)))
        if kind == 'seal_connection':
            closed.add(pair)
        else:
            closed.remove(pair)
        child['closed_pairs'] = [list(p) for p in sorted(closed)]
    else:
        shifts = {tuple(pair):value for pair,value in child['opening_shifts']}
        pair = tuple(sorted((a,b)))
        value = round(shifts.get(pair,0)+rng.choice((-.16,.16)),6)
        shifts[pair] = max(-.35,min(.35,value))
        child['opening_shifts'] = [[list(p),v] for p,v in sorted(shifts.items()) if v]
    return child


def mutate(parent, parent_layout, rng, repairs, *, prefer_topology):
    actions = proposals(parent,parent_layout)
    rng.shuffle(actions)
    if prefer_topology:
        actions.sort(key=lambda action: action[0] in ('shift_opening','move_partition'))
    failures = []
    child, action = parent, None
    for action in actions[:repairs+1]:
        try:
            child = apply_edit(parent,action,rng)
            candidate = realize(child)
            if candidate['layout']['layout_hash']==parent_layout['layout_hash']:
                raise ValueError('layout_unchanged')
            return child, candidate, action, failures
        except ValueError as exc:
            failures.append(dict(operation=action, issue=str(exc)))
    return child, None, action, failures
