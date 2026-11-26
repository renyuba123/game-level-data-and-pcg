from common import ROOT, WORK, GODOT, command, write_json

results = {}
for name, flags in [("chase_test", []), ("editor_preview_test", ["--editor"])]:
    try:
        elapsed = command([GODOT,"--headless","--path",ROOT,*flags,"--script",f"res://scripts/{name}.gd"],WORK/f"{name}.log",120)
        results[name] = {"passed": True, "seconds": elapsed}
    except RuntimeError as exc:
        results[name] = {"passed": False, "error": str(exc)}
write_json(WORK/"runtime_checks.json",results)
print(results)
raise SystemExit(0 if all(r["passed"] for r in results.values()) else 1)
