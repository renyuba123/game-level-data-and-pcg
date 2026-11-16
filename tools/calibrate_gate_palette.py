"""Inspect the supplied Depthmap capture against registered VGA Gate Counts points."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parents[1]
image = Image.open(root / "maps/ratking/gate_counts_depthmap_original.png").convert("RGB")
pixels = image.load()
rows = list(csv.DictReader((root / "maps/ratking/vga_points.csv").open(encoding="utf-8-sig")))
points = [(float(r["x_ai"]), float(r["y_ai"]), float(r["Gate_Counts"])) for r in rows]
palette = ["#3333dd", "#3388dd", "#22ccdd", "#22ccbb", "#22dd88",
           "#88dd22", "#bbcc22", "#ddcc22", "#dd8833", "#dd3333"]
colors = [tuple(bytes.fromhex(c[1:])) for c in palette]


def cls(x, y):
    px, py = int(round(x)), int(round(y))
    if px < 0 or py < 0 or px >= image.width or py >= image.height:
        return -1
    rgb = pixels[px, py]
    distances = [sum((rgb[i] - color[i]) ** 2 for i in range(3)) for color in colors]
    k = min(range(len(colors)), key=lambda j: distances[j])
    return k if distances[k] < 1100 else -1


def evaluate(scale, dx, dy):
    # Image Y increases downwards; AI PDF coordinates increase upwards.
    samples = [(value, cls(scale * x + dx, -scale * y + dy))
               for x, y, value in points]
    valid = [(v, k) for v, k in samples if k >= 0]
    if len(valid) < 2000:
        return (-1, valid)
    # The native palette is ordered, so a good registration has positive
    # value/color correlation. Coverage also selects cell interiors.
    mv = sum(v for v, _ in valid) / len(valid)
    mk = sum(k for _, k in valid) / len(valid)
    cov = sum((v - mv) * (k - mk) for v, k in valid)
    vv = sum((v - mv) ** 2 for v, _ in valid)
    kk = sum((k - mk) ** 2 for _, k in valid)
    corr = cov / math.sqrt(vv * kk) if vv and kk else 0
    return (corr + len(valid) / len(points) * 0.05, valid)


best = (-1, None, None, None, None)
for scale_milli in range(447, 460, 2):
    scale = scale_milli / 1000
    for dx in range(-26, -4, 2):
        for dy in range(537, 560, 2):
            score, valid = evaluate(scale, dx, dy)
            if score > best[0]:
                best = (score, scale, dx, dy, valid)
for scale_milli in range(round(best[1] * 10000) - 15, round(best[1] * 10000) + 16, 5):
    scale = scale_milli / 10000
    for dx_tenth in range(round(best[2] * 10) - 15, round(best[2] * 10) + 16, 5):
        dx = dx_tenth / 10
        for dy_tenth in range(round(best[3] * 10) - 15, round(best[3] * 10) + 16, 5):
            dy = dy_tenth / 10
            score, valid = evaluate(scale, dx, dy)
            if score > best[0]:
                best = (score, scale, dx, dy, valid)

score, scale, dx, dy, valid = best
print("fit", score, "scale", scale, "dx", dx, "dy", dy, "matched", len(valid))
by_color = defaultdict(list)
for value, index in valid:
    by_color[index].append(value)
for index, color in enumerate(palette):
    values = sorted(by_color[index])
    if values:
        print(index, color, len(values), min(values),
              values[len(values) // 10], values[len(values) // 2],
              values[len(values) * 9 // 10], max(values))

# Find the ten monotone value bands that most closely reproduce the native
# point colors at the registered cell centers. This is a derived calibration,
# not an assertion about Depthmap's undocumented palette thresholds.
sorted_valid = sorted(valid)
n = len(sorted_valid)
dp = [[-10**9] * (n + 1) for _ in palette]
back = [[0] * (n + 1) for _ in palette]
dp[0][0] = 0
for end in range(1, n + 1):
    dp[0][end] = dp[0][end - 1] + (sorted_valid[end - 1][1] == 0)
for band in range(1, len(palette)):
    best_prefix, best_start = -10**9, 0
    matches = 0
    for end in range(n + 1):
        if end:
            matches += sorted_valid[end - 1][1] == band
        candidate = dp[band - 1][end] - matches
        if candidate > best_prefix:
            best_prefix, best_start = candidate, end
        dp[band][end] = matches + best_prefix
        back[band][end] = best_start
ends = [n]
for band in range(len(palette) - 1, 0, -1):
    ends.append(back[band][ends[-1]])
ends.reverse()
print("optimized matches", dp[-1][-1], "of", n)
for band, end in enumerate(ends[:-1]):
    low = sorted_valid[end - 1][0] if end else None
    high = sorted_valid[end][0] if end < n else None
    print("boundary", band, low, high)

saved = json.loads((root / "maps/ratking/gate_counts_palette.json").read_text(encoding="utf-8"))
assert saved["source_image_sha256"] == hashlib.sha256(
    (root / "maps/ratking/gate_counts_depthmap_original.png").read_bytes()).hexdigest()
assert saved["matched_cell_centers"] == n
assert saved["matching_palette_assignments"] == dp[-1][-1]
assert len(saved["colors"]) == len(palette)
