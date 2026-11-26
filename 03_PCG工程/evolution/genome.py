from pymoo.core.variable import Real, Integer, Binary, Choice

def variables():
    result = {f"R{i:02d}_{axis}": Real(bounds=(.88, 1.12)) for i in range(1, 12) for axis in ("width", "height")}
    result.update({"slope_cut": Real(bounds=(1.25, 2.0)), "bevel": Real(bounds=(.35, .65)),
        "swap_upper": Binary(), "swap_side": Binary(), "remove_normal": Integer(bounds=(-1, 14)),
        "block_x": Real(bounds=(-.35, .35)), "block_y": Real(bounds=(-.35, .35)),
        "block_terminal_offset": Real(bounds=(.9, 1.3)),
        "spawn_room": Choice(options=[2, 3, 4, 5, 7, 8]), "boss_room": Choice(options=[0, 6, 9])})
    for i in range(15):
        result[f"priority_{i}"] = Real(bounds=(0., 1.))
        result[f"door_width_{i}"] = Real(bounds=(.78, 1.))
        result[f"door_offset_{i}"] = Real(bounds=(.3, .7))
    return result

def native(genes):
    return {key: value.item() if hasattr(value, "item") else value for key, value in genes.items()}
