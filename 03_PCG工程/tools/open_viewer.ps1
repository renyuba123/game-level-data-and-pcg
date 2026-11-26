param(
    [string]$Run = 'shell_sampling_focused_g20_v1',
    [ValidateRange(1024,65535)][int]$Port = 8503
)
$ErrorActionPreference='Stop'
if ($Run -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Run must be an existing run ID.' }
$projectRoot=Split-Path -Parent $PSScriptRoot
$archiveRoot='F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs'
$runPath=Join-Path $archiveRoot $Run
if (-not (Test-Path -LiteralPath (Join-Path $runPath 'config_snapshot.json'))) { throw "No registered run: $Run" }
$viewerPython=Join-Path $env:LOCALAPPDATA 'RatKingPCG\viewer\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $viewerPython)) { throw "Viewer Python is missing: $viewerPython" }
Push-Location -LiteralPath $projectRoot
try {
    $oldPythonPath=$env:PYTHONPATH
    $env:PYTHONPATH=$projectRoot
    & $viewerPython -B -m streamlit run full_pcg/viewer/app.py --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false --theme.base light -- --run $runPath --godot 'D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe'
    if ($LASTEXITCODE -ne 0) { throw "Viewer exited with code $LASTEXITCODE" }
} finally { $env:PYTHONPATH=$oldPythonPath; Pop-Location }
