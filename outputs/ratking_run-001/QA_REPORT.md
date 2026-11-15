# Rat King run-001 — revision QA (2026-11-15)

## Illustrator deliverable

- Original: `鼠王关玩家路线图001.ai`; SHA-256 `66238BC3F75C78F018A90749B2130A3CF0ED021977BBFBAD4F8BFF1D86CA2542`. Its bytes were not changed.
- Edited: `outputs/ratking_run-001/ratking_run-001_edited.ai`; SHA-256 `B5CAE22FE04B7CC3DDA931F23F80F506FA8440DAE2667B804913CB0434FF3156`.
- Executed `style_working_copy.jsx` through Illustrator 2026's COM/ExtendScript interface. Illustrator saved the edited document with PDF compatibility. A separate Illustrator call reopened it successfully and reported 22 layers; the PDF-compatible reader also found one page and 22 optional-content layers.
- `movement_from_edited_ai`, `combat_from_edited_ai`, and `convex_from_edited_ai` SVG/PNG pairs were exported by Illustrator from the edited document's layer views. PNGs were visually inspected. Previous preview images generated independently were removed.
- The two previous byte-identical AI copies in `runs/` and `source/001/` were removed after reopening the edited file. A project scan now finds exactly two `.ai` files: original and edited.
- Figure limitation: room labels are provisional and the raw convex fill is saturated. The movement view labels the user-confirmed start and end direction but does not yet show a fully verified arrow sequence. The combat view retains original symbols without event ID labels or a confirmed action legend. Do not use these figures as final numerical syntax plots.

## First-run data

- User confirmed green Spawn E024 as the beginning and the left endpoint near Transform as the end. The exact Transform marker among E001/E002 is still unresolved.
- PDF Route paint geometry yields 44 movement segments and 88 endpoint records. A filled arrowhead was excluded. Paint 45 was placed between paints 9 and 10; paint 13 was reversed to connect neighbors. Local order was inferred from the user-confirmed overall direction and endpoint continuity, **not** verified frame by frame. A gap of 8.64 PDF points remains before paint 17.
- Route and event coordinates use the PDF/AI page-point system, origin lower-left, Y up. No metre scale or game timestamps are known. Validation script result: PASS, with warnings that ordered rows remain unverified against video.
- `rooms.json` assigns provisional R01–R10 based on the visible convex-map colors. The apparent lower-center L-shaped region was split provisionally as R05/R06. Exact polygon outlines, genuine convex IDs, passable doors and room-level route/event assignment remain to be verified against the graph and plan. `connections.json` remains empty intentionally.

## DepthmapX and visibility

- `shuwangguan.graph` is a DepthmapX binary. Inspection confirms `Convex Map`, `VGA Map`, `Choice`, `Integration [HH]`, `Visual Integration [HH]`, `Visual Mean Depth`, and `Connectivity` fields. This proves the data sets are present, but does not yet export their numeric rows or geometry.
- The existing Illustrator `depthmap` layer shows colored space regions. It is **not** an identified VGA/Visibility metric view. No visibility heatmap or syntax-route correlation has been claimed or generated.
- Required next export: Convex Map polygons and node attributes; VGA point coordinates and values for a named visibility attribute, with map origin, pixel spacing and legend. Register both to the AI plan before assigning final room IDs or adding a Visibility figure to the edited AI.

## Remaining checks

1. Resolve Route paint 16→17 gap and identify the exact Transform marker at the end from the video.
2. Verify room convexity, each door connection and coordinate registration to the graph.
3. Confirm event-layer semantics, including duplicate `Break` and `Transform`, before computing event rates or publishing a legend.
4. Export actual Convex Map and VGA metrics from DepthmapX and add a separate visibility layer/view to the edited AI.
