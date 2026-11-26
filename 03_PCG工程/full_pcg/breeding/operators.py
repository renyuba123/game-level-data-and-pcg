"""Reshape the recipient inside its shell using a compatible donor room group."""

from copy import deepcopy
import math

from shapely.geometry import box

from full_pcg.common import digest
from full_pcg.shell_genome import SIBLINGS, apply_edit, graph, polygons, proposals, realize, serialize
from full_pcg.shell_layout import corner_l, unequal_pair
from full_pcg.shell_pilot import crowding, fronts


def parent_pair(pool, rng):
    """Binary tournaments prefer the better front, then less crowded candidates."""
    keys = {}
    for rank, front in enumerate(fronts(pool)):
        distances = crowding(front)
        for row in front:
            keys[row["id"]] = rank, -distances[row["id"]]

    def pick(rows):
        candidates = rng.sample(rows, min(2, len(rows)))
        return min(candidates, key=lambda r: keys.get(r["id"], (math.inf, 0)))

    first = pick(pool)
    remaining = [row for row in pool if row["layout_hash"] != first["layout_hash"]]
    return first, pick(remaining) if remaining else None


def interfaces(layout, members):
    return {edge[1] if edge[0] in members else edge[0] for edge in graph(layout).edges
            if (edge[0] in members) != (edge[1] in members)}


def locus(genome, host, pocket):
    cells = polygons(genome["partitions"])
    return tuple((name, cells[name].wkb_hex) for name in (host, pocket) if name in cells)


def graft(recipient, donor, recipient_layout, donor_layout, host, pocket):
    """Transfer the donor's corner and dimensions into the recipient's mother cell."""
    cells = polygons(recipient["partitions"])
    donor_cells = polygons(donor["partitions"])
    members = {host, pocket}
    receiver_edges = interfaces(recipient_layout, members)
    donor_edges = interfaces(donor_layout, members)
    if host not in cells or host not in donor_cells or not all(1 <= len(x) <= 3 for x in (receiver_edges, donor_edges)):
        raise ValueError("incompatible_boundary_interfaces")
    envelope = cells[host].union(cells.get(pocket, cells[host]))
    donor_envelope = donor_cells[host].union(donor_cells.get(pocket, donor_cells[host]))
    if any(p.geom_type != "Polygon" or p.interiors or abs(p.area-box(*p.bounds).area) > 1e-5
           for p in (envelope, donor_envelope)):
        raise ValueError("nonrectangular_mother_cell")
    child = deepcopy(recipient)
    cells[host] = envelope
    if pocket in donor_cells:
        x0, z0, x1, z1 = donor_cells[pocket].bounds
        x, z, xx, zz = envelope.bounds
        east = abs(x1 - donor_envelope.bounds[2]) < 1e-5
        north = abs(z1 - donor_envelope.bounds[3]) < 1e-5
        w, h = x1-x0, z1-z0
        left, bottom = (xx-w if east else x), (zz-h if north else z)
        # Use the exact recipient bounds along exterior walls before decoding.
        small = box(left, bottom, xx if east else x+w, zz if north else z+h)
        large = envelope.difference(small)
        if not corner_l(large, small) or not unequal_pair(host, large, pocket, small):
            raise ValueError("donor_corner_violates_receiver_clearance")
        cells[host], cells[pocket] = large, small
    else:
        cells.pop(pocket, None)
        child["closed_pairs"] = [pair for pair in child["closed_pairs"] if pocket not in pair]
        child["opening_shifts"] = [entry for entry in child["opening_shifts"] if pocket not in entry[0]]
    child["partitions"] = serialize(cells)
    child["edited_partition"] = True
    base = polygons(recipient["partitions"])
    if cells[host].equals(base[host]) and (pocket in cells) == (pocket in base):
        raise ValueError("donor_locus_unchanged")
    packet = realize(child)
    if interfaces(packet["layout"], members) != receiver_edges:
        raise ValueError("recipient_interfaces_changed")
    return child, packet, {
        "kind": "crossover", "operation": ["graft_corner", host, pocket],
        "before_genome": digest(recipient), "after_genome": digest(child),
        "recipient_interfaces": sorted(receiver_edges), "donor_interfaces": sorted(donor_edges),
        "donor_partition": [["host", host], ["pocket", pocket]],
        "inherited_locus_hash": digest(locus(child, host, pocket)),
    }


def breed(first, second, packets, rng, crossover_probability, max_checks, mutation_range):
    base = first["genome"]
    base_packet = packets[first["layout_hash"]]
    genome, packet, operations, failures = base, base_packet, [], []
    parents = [first["id"]]
    attempted_pair, protected = None, None
    remaining = max_checks
    if second and rng.random() < crossover_probability:
        attempted_pair = [first["id"], second["id"]]
        regions = list(SIBLINGS)
        rng.shuffle(regions)
        for host, pocket in regions:
            if remaining <= 1:
                break
            remaining -= 1
            try:
                genome, packet, event = graft(base, second["genome"], base_packet["layout"],
                                               packets[second["layout_hash"]]["layout"], host, pocket)
            except ValueError as exc:
                failures.append({"operation": ["graft_corner", host, pocket], "issue": str(exc)})
                continue
            protected = (host, pocket)
            parents.append(second["id"])
            operations.append(event)
            break
    crossed = protected is not None
    target = rng.randint(*mutation_range)
    mutations = 0
    seen = {base_packet["layout"]["layout_hash"], packet["layout"]["layout_hash"]}
    if second:
        seen.add(second["layout_hash"])
    while remaining and mutations < target:
        actions = proposals(genome, packet["layout"])
        rng.shuffle(actions)
        geometric = {"move_partition", "shift_opening"}
        prefer_geometry = rng.random() < 0.5
        actions.sort(key=lambda action: (action[0] in geometric) != prefer_geometry)
        for action in actions:
            if not remaining:
                break
            if protected and action[0] in {"split", "merge", "move_partition"} and protected[0] == action[1]:
                continue
            remaining -= 1
            try:
                changed = apply_edit(genome, action, rng)
                evaluated = realize(changed)
                key = evaluated["layout"]["layout_hash"]
                if key in seen:
                    raise ValueError("layout_unchanged_or_reverted")
                if protected and (locus(changed, *protected) != locus(genome, *protected) or
                                  interfaces(evaluated["layout"], set(protected)) !=
                                  interfaces(packet["layout"], set(protected))):
                    raise ValueError("mutation_lost_crossover_inheritance")
            except ValueError as exc:
                failures.append({"operation": action, "issue": str(exc)})
                continue
            operations.append({"kind": "mutation", "operation": action,
                               "before_genome": digest(genome), "after_genome": digest(changed)})
            seen.add(key)
            genome, packet = changed, evaluated
            mutations += 1
            break
        else:
            break
    if operations and packet["layout"]["layout_hash"] in {first["layout_hash"], second["layout_hash"] if second else None}:
        failures.append({"issue": "offspring_matches_a_parent"})
        packet = None
    request = {
        "parents": parents, "attempted_parents": attempted_pair, "genome": genome,
        "operation": operations[0]["operation"] if operations else None, "operations": operations,
        "failures": failures, "crossover": "applied" if crossed else "fallback" if attempted_pair else "not_sampled",
        "mutation_target": target, "mutation_count": mutations, "checks": max_checks-remaining,
    }
    return request, packet if operations else None
