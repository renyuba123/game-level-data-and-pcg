"""Read the candidate pointmap CSV saved by DepthmapX during evaluation."""

import csv
from dataclasses import dataclass
from math import isfinite

from full_pcg.common import read

DISTANCE = "Metric Mean Shortest-Path Distance"
DEPTHMAP_METRICS = {
    "Visual Integration [HH]": "视觉整合度（HH）",
    "Connectivity": "可视连接度",
    DISTANCE: "平均最短路径距离",
}
DEPTHMAP_STATES = {"initial": "初始状态", "all_open": "可破坏通道全开"}


@dataclass(frozen=True)
class DepthmapGrid:
    spacing_m: float
    positions_m: tuple
    values: dict
    source_run: str


def read_depthmap_grid(archive_root, layout_hash, state, comparison):
    directory = archive_root / "space" / layout_hash / "candidate" / state
    csv_path = directory / "metrics.csv"
    manifest_path = directory / "complete.json"
    if not csv_path.is_file() or not manifest_path.is_file():
        return None
    manifest = read(manifest_path)
    grid = comparison["grid_drawing_units"]
    if (type(grid) is not int or grid <= 0 or manifest["recipe"]["grid"] != grid
            or manifest["key"] != comparison[state]["candidate_key"]):
        raise ValueError("点网格与归档的 Depthmap 分析记录不一致")
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"x", "y", *DEPTHMAP_METRICS} <= set(reader.fieldnames or ()):
            raise ValueError("Depthmap 导出缺少所需的点位或指标列")
        positions, values = [], {metric: [] for metric in DEPTHMAP_METRICS}
        for row in reader:
            x, z = float(row["x"]), float(row["y"])
            if not all(isfinite(p) and p % grid == 0 for p in (x, z)):
                raise ValueError("Depthmap 点位与分析网格间距不一致")
            positions.append((x/1000, z/1000))
            for metric, column in values.items():
                value = float(row[metric])
                if not isfinite(value) or value < 0:
                    raise ValueError("Depthmap 导出含无效指标值")
                column.append(value/1000 if metric == DISTANCE else value)
    if not (manifest["point_count"] == comparison[state]["candidate"]["point_count"]
            == len(positions) == len(set(positions)) > 0):
        raise ValueError("Depthmap 点数与归档记录不一致")
    return DepthmapGrid(grid/1000, tuple(positions),
                       {metric: tuple(column) for metric, column in values.items()}, archive_root.name)
