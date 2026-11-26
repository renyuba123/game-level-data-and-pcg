# Full-PCG development status

This is an in-progress implementation, not the completed upgrade.

## Implemented and run

- Separate `full_pcg` package; Legacy generator and search_v1 are unchanged.
- Variable planar anchor graphs, 8–18 rooms, variable cycles and semantic gates.
- Rectangle, chamfer, trapezoid, L and notch contours; individual rotations.
- Deterministic corridor routing, explicit common-room entry junction mapping, polygon floor/walls, two obstacles and role-sized navigation triangles.
- Validation of initial/all-open polygon reachability, reachable Boss smash faces, escape paths, endpoint connectors and detour bounds.
- Versioned geometry audit directories keyed by source/configuration hashes; previews and JSON per seed.
- Latest completed 100-seed audit: 90 valid, 88 exact unlabelled topology classes, room counts 8–18, cycle counts 2–7. Rejections: six short escape paths, two missing break shortcuts, two excessive detours.
- New reference scenario: DXF R01 player, R09 Boss, R11 exit. Initial R11 is break-gated; finite initial static escape time must NOT be invented. DXF outer-shell reconstruction and doorway medial anchors resolve analysis-partition gaps and off-grid corridors. Break-open walking-distance lower bound is about 20.135 model metres / 5 m/s = 4.027 s; the configured 4 s minimum remains conservative.

## Not yet accepted

- Phase 2 is not complete: actual Godot decode/physics/navigation tests remain, as does explicit geometric graph reconstruction versus the intended graph.
- The reference protocol is not frozen. Functional-area accounting, opened-through geometry and dynamic Boss schedule still require checks.
- The initial anchor lattice is a packing prior, not unrestricted room placement. Sampling is not evolutionary history.
- Operators support add/delete room, add/delete edge, shape/position/rotation/door/spawn/obstacle mutation. A bounded one-interface branch crossover is implemented; the approved general 2–3 interface crossover is not yet implemented.
- Full-PCG evaluation, NSGA-II engine, committed Generation 0–20 records, Godot replay, videos, 12-candidate 3D validation and the 6048-evaluation comparison are still pending.
- Gate Counts and Convex Choice remain excluded. No new optimized candidate or completed experiment is claimed.

## Next work

1. Finish Phase 2 geometry-to-topology and Godot acceptance without loosening collision rules.
2. Freeze the new comparison protocol; implement functional/scale normalization and stateful simulation adapter.
3. Complete graph crossover and deterministic logger/engine with resume and worker-count equivalence tests.
4. Add offline 2D Evolution Viewer and real generation exports, followed by 3D selection/play tests.
5. Run pilot, one complete 0–20 run, then matched three-arm experiments and report.
