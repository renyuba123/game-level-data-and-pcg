# Full-PCG v2 development

Independent subsystem. Legacy scripts and search_v1 remain unchanged.

Current implementation: variable planar anchor graphs, room count and shape/rotation, graph edge deletion, explicit portals, deterministic corridor routing and polygon union. Python layout is the single geometry source. Stable room/edge IDs and versioned JSON are used throughout.

Initial anchor sampling uses a grown planar lattice as a packing aid, not a fixed room graph. It is still a geometric prior: the development report must retain this limitation. It does not yet implement the approved graph crossover, independent topology mutation, optimization, replay or complete validation. Do not describe the initial geometry audit as final Phase 2 acceptance.

Run with the existing evolution virtual environment: `python -m full_pcg generate --seeds 1:100`.
