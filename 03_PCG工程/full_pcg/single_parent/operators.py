"""Archive sampling and single-parent edits for the approved shell family."""

from collections import Counter
from math import isfinite
from random import Random

from full_pcg.common import digest
from full_pcg.shell_genome import SIBLINGS, apply_edit, graph, polygons, proposals, realize
from full_pcg.shell_layout import corner_l
from full_pcg.shell_pilot import eligible, fronts


def sampling_pool(records):
    """Use the first eligible occurrence of a layout and count all its child requests."""
    counts = Counter(row["parent_layout_hash"] for row in records if row.get("parents"))
    distinct = {}
    for row in records:
        if eligible(row) and all(isfinite(value) for value in row["scores"].values() if value is not None):
            distinct.setdefault(row["layout_hash"], row)
    return [
        {"id": row["id"], "layout_hash": key, "rank": rank,
         "prior_requests": counts[key], "weight": 1 / (rank * (1 + counts[key]))}
        for rank, front in enumerate(fronts(distinct.values()), 1)
        for row in front
        for key in (row["layout_hash"],)
    ]


def other_edges(layout, region):
    return {tuple(sorted((a, b))) for a, b in graph(layout).edges if {a, b}.isdisjoint(region)}


def boundary_neighbors(layout, region):
    return {b if a in region else a for a, b in graph(layout).edges if (a in region) != (b in region)}


def rewrite_region(genome, packet, action, rng, *, preferred_corner=None):
    """Resubdivide a single mother cell and rebuild its openings from shared walls."""
    _, host, pocket = action
    members = {host, pocket}
    old = polygons(genome["partitions"])
    change = "move_partition" if pocket in old else "split"
    child = apply_edit(genome, (change, host, pocket), rng, preferred_corner=preferred_corner)
    new = polygons(child["partitions"])
    if pocket in old:
        # A full edit relocates the corner room, rather than only resizing it.
        old_contact = tuple(abs(a-b) < 1e-5 for a,b in zip(old[pocket].bounds, old[host].union(old[pocket]).bounds))
        new_contact = tuple(abs(a-b) < 1e-5 for a,b in zip(new[pocket].bounds, new[host].union(new[pocket]).bounds))
        if new_contact == old_contact:
            raise ValueError("same_corner")
    child["closed_pairs"] = [pair for pair in child["closed_pairs"] if not set(pair) <= members]
    child["opening_shifts"] = [entry for entry in child["opening_shifts"] if not set(entry[0]) <= members]
    result = realize(child)
    before, after = packet["layout"], result["layout"]
    if other_edges(before, members) != other_edges(after, members):
        raise ValueError("outside_adjacency_changed")
    if boundary_neighbors(before, members) != boundary_neighbors(after, members):
        raise ValueError("region_interface_changed")
    return child, result


def describe_edit(before, after, layout_before, layout_after, action):
    edge_sets = [{tuple(sorted(pair)) for pair in graph(layout).edges}
                 for layout in (layout_before, layout_after)]
    old, new = (dict(genome["partitions"]) for genome in (before, after))
    partitions = {name: {"before": old.get(name), "after": new.get(name)}
                  for name in sorted(old.keys() | new.keys()) if old.get(name) != new.get(name)}
    return {
        "kind": action[0], "operation": list(action),
        "before_genome": digest(before), "after_genome": digest(after),
        "partitions": partitions,
        "opening_shifts": [before["opening_shifts"], after["opening_shifts"]],
        "closed_pairs": [before["closed_pairs"], after["closed_pairs"]],
        "adjacency_added": [list(pair) for pair in sorted(edge_sets[1] - edge_sets[0])],
        "adjacency_removed": [list(pair) for pair in sorted(edge_sets[0] - edge_sets[1])],
    }


def archive_reference_slots(spec, generation):
    """Give the new experiment about one reference attempt per ten requests."""
    if spec.get("schema") != "shell-single-parent-experiment/1" or not generation:
        return set()
    schedule = Random(f"{spec['optimizer_seed']}:reference-slots:{generation}")
    count, remainder = divmod(spec["population"], 10)
    count += schedule.randrange(10) < remainder
    return set(schedule.sample(range(spec["population"]), count))


def corner_position(cells, host, pocket):
    large, small = cells.get(host), cells.get(pocket)
    if large is None or small is None or not corner_l(large, small):
        return None
    _, _, right, top = large.union(small).bounds
    return abs(small.bounds[2] - right) < 1e-5, abs(small.bounds[3] - top) < 1e-5


def edit_with_reference(parent, base, rng, spec, references):
    """Use a historical corner as a hint for one region on the actual parent's shell."""
    original = parent["genome"]
    cells = polygons(original["partitions"])
    options = {}
    for exemplar in references:
        if exemplar["layout_hash"] == parent["layout_hash"]:
            continue
        pattern = polygons(exemplar["genome"]["partitions"])
        for host, pocket in SIBLINGS:
            if host not in cells or host not in spec["full_edit_regions"]:
                continue
            corner = corner_position(pattern, host, pocket)
            if corner is not None and corner != corner_position(cells, host, pocket):
                options.setdefault((host, pocket, corner), exemplar)

    candidates = list(options)
    rng.shuffle(candidates)
    failures = []
    for host, pocket, corner in candidates[:min(3, spec["max_repairs"]-1)]:
        exemplar = options[host, pocket, corner]
        provenance = {"id": exemplar["id"], "layout_hash": exemplar["layout_hash"],
                      "region": host, "corner": list(corner)}
        action = ("archive_reference", host, pocket)
        try:
            child, packet = rewrite_region(original, base, action, rng, preferred_corner=corner)
            if packet["layout"]["layout_hash"] == parent["layout_hash"]:
                raise ValueError("layout_unchanged")
        except ValueError as exc:
            failures.append({"operation": list(action), "reference": provenance, "issue": str(exc)})
            continue
        operation = describe_edit(original, child, base["layout"], packet["layout"], action)
        operation["reference"] = provenance
        return {
            "parents": [parent["id"]], "parent_layout_hash": parent["layout_hash"],
            "genome": child, "genome_hash": digest(child),
            "edit": "archive_reference", "edit_target": 1, "archive_reference": provenance,
            "operation": list(action), "operations": [operation], "failures": failures,
            "checks": len(failures)+1,
        }, packet

    row, packet = edit(parent, base, rng, spec | {"max_repairs": spec["max_repairs"]-len(failures)})
    row["archive_reference_attempted"] = True
    row["checks"] += len(failures)
    row["failures"] = (failures or [{"operation": ["archive_reference"],
                                    "issue": "no_compatible_archive_corner"}]) + row["failures"]
    return row, packet


def edit(parent, base, rng, spec):
    genome, packet = parent["genome"], base
    full = rng.random() < spec["full_edit_probability"]
    target = 1 if full else rng.randint(*spec["diff_edits"])
    single_step = not full and spec.get("diff_operator") == "single_opening_or_partition"
    if single_step:
        target = 1
    operations, failures = [], []
    seen = {base["layout"]["layout_hash"]}
    checks = 0
    while checks < spec["max_repairs"] and len(operations) < target:
        if full:
            actions = [("rewrite_region", host, pocket) for host, pocket in SIBLINGS
                       if host in spec["full_edit_regions"] and host in dict(genome["partitions"])]
        else:
            actions = proposals(genome, packet["layout"])
            if single_step:
                actions = [action for action in actions if action[0] in ("shift_opening", "move_partition")]
        if not actions:
            break
        rng.shuffle(actions)
        for action in actions:
            if checks == spec["max_repairs"]:
                break
            checks += 1
            try:
                if full:
                    child, result = rewrite_region(genome, packet, action, rng)
                else:
                    child = apply_edit(genome, action, rng)
                    result = realize(child)
                key = result["layout"]["layout_hash"]
                if key in seen:
                    raise ValueError("layout_unchanged_or_reverted")
            except ValueError as exc:
                failures.append({"operation": list(action), "issue": str(exc)})
                continue
            operations.append(describe_edit(genome, child, packet["layout"], result["layout"], action))
            genome, packet = child, result
            seen.add(key)
            break
    unchanged = bool(failures) and all(f["issue"] == "layout_unchanged_or_reverted" for f in failures)
    return {
        "parents": [parent["id"]], "parent_layout_hash": parent["layout_hash"],
        "genome": genome, "genome_hash": digest(genome),
        "edit": "full" if full else "diff", "edit_target": target,
        "operation": operations[0]["operation"] if operations else None,
        "operations": operations, "failures": failures, "checks": checks,
    }, packet if operations or unchanged else None
