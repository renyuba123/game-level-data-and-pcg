"""Compare the three Phase 4 sampling archives with a fixed four-axis reference."""

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median

import networkx as nx
import numpy as np
from pymoo.indicators.hv import HV

from combat_pcg.godot_batch import file_hash
from full_pcg.common import digest, read, write
from full_pcg.shell_pilot import OBJECTIVES, eligible
from full_pcg.viewer.archive import Archive, display_q, require, room_graph


def generation_metrics(archive, arm):
    generations, rows = archive.arms[arm]
    hv = HV(ref_point=np.ones(len(OBJECTIVES)))
    topologies = {}
    topology_by_layout = {}
    birth_types = set()
    seen_layouts = set()
    history_q = None
    curves = []

    def exact_topology(row):
        key = row["layout_hash"]
        if key not in topology_by_layout:
            graph = room_graph(archive.layout(row))
            fingerprint = nx.weisfeiler_lehman_graph_hash(graph)
            bucket = topologies.setdefault(fingerprint, [])
            index = next((i for i, exemplar in enumerate(bucket)
                          if nx.is_isomorphic(graph, exemplar)), len(bucket))
            if index == len(bucket):
                bucket.append(graph)
            topology_by_layout[key] = (fingerprint, index)
        return topology_by_layout[key]

    for n, g in generations.items():
        cohort = [rows[i] for i in g.requests]
        front = [rows[i] for i in g.cumulative_pareto]
        q_now = [display_q(rows[i]) for i in g.survivors if eligible(rows[i])]
        valid = [r for r in cohort if eligible(r)]
        unique_new = {r["layout_hash"] for r in valid} - seen_layouts
        seen_layouts.update(r["layout_hash"] for r in valid)
        if valid:
            best = max(map(display_q, valid))
            history_q = best if history_q is None else max(history_q, best)
        types = {exact_topology(row) for row in cohort
                 if row.get("layout_hash") and row["status"] in {"COMPLETE_DRAFT", "UNCERTAIN"}}
        birth_types.update(types)
        parent_deltas = [
            {m: r["scores"][m] - rows[r["parents"][0]]["scores"][m] for m in OBJECTIVES}
            | {"Q": display_q(r) - display_q(rows[r["parents"][0]])}
            for r in valid if r["parents"] and eligible(rows[r["parents"][0]])
        ]
        scores = np.asarray([[r["scores"][key] for key in OBJECTIVES] for r in front])
        curves.append({
            "generation": n, "requests": len(cohort), "status": dict(Counter(r["status"] for r in cohort)),
            "historical_best": {m: max((r["scores"][m] for r in front), default=None) for m in OBJECTIVES},
            "q_survivor_max": max(q_now, default=None), "q_survivor_mean": mean(q_now) if q_now else None,
            "q_historical_max": history_q,
            "cumulative_hv": float(hv(1 - scores / 100)) if len(front) else 0.0,
            "new_non_dominated": len(unique_new & {r["layout_hash"] for r in front}),
            "parent_score_pairs": len(parent_deltas),
            "median_child_minus_parent": {
                m: median(d[m] for d in parent_deltas) for m in (*OBJECTIVES, "Q")
            } if parent_deltas else None,
            "parent_source": dict(Counter(r["parent_sample"].get("source", "archive")
                                          for r in cohort if r["parents"])),
            "parent_draws_outside_previous_survivors": sum(
                r["parents"][0] not in generations[n-1].survivors for r in cohort if r["parents"]
            ),
            "fallback_parent_draws": sum(r["parent_sample"].get("fallback", False)
                                         for r in cohort if r["parents"]),
            "candidate_topology_classes": len(types),
            "cumulative_candidate_topology_classes": len(birth_types),
        })
    return curves


def operator_metrics(rows):
    groups = {}
    for child in rows.values():
        if child["parents"]:
            groups.setdefault(child["edit"], []).append(child)
    result = {}
    for edit, children in groups.items():
        pairs = [(r, rows[r["parents"][0]]) for r in children
                 if eligible(r) and eligible(rows[r["parents"][0]])]
        result[edit] = {
            "status": dict(Counter(r["status"] for r in children)),
            "complete_pairs": len(pairs),
            "median_delta": {m: median(a["scores"][m] - b["scores"][m] for a, b in pairs)
                             for m in OBJECTIVES} if pairs else None,
            "failure_issues": dict(Counter(f["issue"] for r in children for f in r["failures"])),
        }
    return result


def compare_archives(paths):
    archives = [Archive(path) for path in paths]
    arms = ("genetic", "genetic", "random")
    first_config = archives[0].config
    first_registration = archives[0].registration
    ignored = {"run_id", "sampling"}
    baseline = {k: v for k, v in first_config.items() if k not in ignored}
    reference_g0 = None
    result = {}
    comparison_implementation = archives[1].registration["implementation"]
    allowed_changes = {"full_pcg/single_parent/experiment.py", "full_pcg/single_parent/run.py",
                       "full_pcg/single_parent/sampling.py"}
    for label, archive, arm, sampling in zip("ABC", archives, arms, ("archive", "focused", "independent")):
        spec, registration = archive.config, archive.registration
        require(digest(spec) == registration["config_hash"], f"{label}: config hash mismatch")
        require(spec.get("sampling", "archive") == sampling, f"{label}: unexpected sampling mode")
        require({k: v for k, v in spec.items() if k not in ignored} == baseline,
                f"{label}: shared protocol mismatch")
        for key in ("tools", "combat_hash", "scoring_hash", "total_requests", "official_requests"):
            require(registration[key] == first_registration[key], f"{label}: different {key}")
        registered = registration["implementation"]
        observed_changes = {k for k in registered.keys() | comparison_implementation.keys()
                            if registered.get(k) != comparison_implementation.get(k)}
        require(observed_changes <= (allowed_changes if label == "A" else set()),
                f"{label}: incompatible evaluator or operators: {sorted(observed_changes)}")
        generations, rows = archive.arms[arm]
        require(len(generations) == 21 and len(rows) == 168 and all(len(g.requests) == 8 for g in generations.values()),
                f"{label}: incomplete 168-request comparison arm")
        initial = []
        for identity in generations[0].requests:
            row = rows[identity]
            layout_hash = row["layout_hash"]
            evidence = archive.evidence_folder(row)
            initial.append({
                **{key: row.get(key) for key in ("seed", "layout_hash", "status", "scores", "outcomes")},
                "space_hash": file_hash(archive.root/"space"/layout_hash/"comparison.json") if evidence else None,
                "episode_hashes": read(evidence/"episodes/manifest.json")["episode_hashes"] if evidence else None,
            })
        require(reference_g0 is None or initial == reference_g0, f"{label}: initial evidence differs")
        reference_g0 = initial
        overview = read(archive.root/"overview.json")
        runtime = read(archive.root/"runtime/summary.json")
        curves = generation_metrics(archive, arm)
        result[label] = {
            "archive": str(archive.root), "sampling": sampling, "config_hash": registration["config_hash"],
            "git_commit": registration["git_commit"], "overview": overview, "runtime": runtime,
            "g1_g20_new_non_dominated_rate": sum(g["new_non_dominated"] for g in curves[1:]) / 160,
            "full_score_rate": overview["status"].get("COMPLETE_DRAFT", 0) / 168,
            "generations": curves, "operators": operator_metrics(rows),
        }
    return {"reference": {"objectives": list(OBJECTIVES), "minimum_scores": [0, 0, 0, 0],
                          "normalization": "divide scores by 100", "optimization_seeds": 1,
                          "shared_g0_evidence_hash": digest(reference_g0)},
            "arms": result}


def format_markdown(result):
    arms = result["arms"]
    lines = [
        "# Phase 4 单亲抽样等预算对照实测", "",
        "三组各 168 个请求，共用同一组 G0。累计超体积使用归一化 S/F/P/D、固定零参考点。"
        "本轮使用一个优化种子。", "",
        "| 组别 | G0／G2／G20 累计超体积 | 新布局进前沿（G1–G20） | 完整评分率 | 累计拓扑类 | Godot 局数 | DepthmapX 调用 | 运行分钟 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, arm in arms.items():
        generations = arm["generations"]
        hv = " / ".join(f'{generations[n]["cumulative_hv"]:.6f}' for n in (0, 2, 20))
        runtime = arm["runtime"]
        lines.append(
            f"| {name} | {hv} | {arm['g1_g20_new_non_dominated_rate']:.1%} | "
            f"{arm['full_score_rate']:.1%} | {generations[-1]['cumulative_candidate_topology_classes']} | "
            f"{arm['overview']['new_certified_battles']} | {runtime['counts'].get('depthmap:complete', 0)} | "
            f"{runtime['seconds'].get('invocation', 0) / 60:.1f} |"
        )
    lines.extend(["", "## 最终单项与 Q", "",
                  "| 组别 | 历史最高 S | F | P | D | 历史最高 Q | G20 幸存者平均 Q |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for name, arm in arms.items():
        final = arm["generations"][-1]
        metrics = [final["historical_best"][m] for m in OBJECTIVES]
        metrics.extend((final["q_historical_max"], final["q_survivor_mean"]))
        values = " | ".join(f"{v:.2f}" if v is not None else "—" for v in metrics)
        lines.append(f"| {name} | {values} |")
    a, b, c = (arms[k] for k in "ABC")
    higher_entry = b["g1_g20_new_non_dominated_rate"] > a["g1_g20_new_non_dominated_rate"]
    higher_hv = b["generations"][-1]["cumulative_hv"] > c["generations"][-1]["cumulative_hv"]
    lines.extend(["", "## 后续试验门槛", "",
                  f"- B 的新布局入前沿比例高于 A：{'通过' if higher_entry else '未通过'}。",
                  f"- B 的 G20 累计超体积高于 C：{'通过' if higher_hv else '未通过'}。",
                  "- 下一项为单步编辑对照。" if higher_entry and higher_hv else
                  "- 下一项为按算子核对父子分差、评价状态和失败原因。",
                  "", "## 归档", ""])
    lines.extend(f"- {label}：`{arm['archive']}`，登记 Git `{arm['git_commit']}`。"
                 for label, arm in arms.items())
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("baseline", "focused", "random"):
        parser.add_argument(f"--{argument}", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    result = compare_archives((args.baseline, args.focused, args.random))
    if args.output:
        write(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.markdown:
        args.markdown.write_text(format_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
