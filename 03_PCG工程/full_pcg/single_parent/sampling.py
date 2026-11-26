"""Parent allocation for the Phase 4 research comparison."""

from random import Random

from full_pcg.shell_pilot import OBJECTIVES, crowding, pareto


def focused_slots(spec, generation):
    rng = Random(f"{spec['optimizer_seed']}:focused-slots:{generation}")
    return set(rng.sample(range(8), 6))


def focused_pool(records, survivors, archive):
    """Keep up to eight distinct layouts across current and historical fronts."""
    by_layout = {entry["layout_hash"]: entry for entry in archive}
    front_ids = [pareto(survivors), pareto(records.values())]
    selected = {}

    def add(row):
        key = row["layout_hash"]
        if key in by_layout and len(selected) < 8:
            selected.setdefault(key, by_layout[key])

    for ids in front_ids:
        if ids:
            for objective in OBJECTIVES:
                identity = min(ids, key=lambda i: (-records[i]["scores"][objective], i))
                add(records[identity])
    for ids in front_ids:
        rows = [records[i] for i in ids]
        if rows:
            spacing = crowding(rows)
            for row in sorted(rows, key=lambda r: (-spacing[r["id"]], r["id"])):
                add(row)
    return list(selected.values())
