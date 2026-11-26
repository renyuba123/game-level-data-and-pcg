# Run or resume the two new arms after the smoke archive has passed verification.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $project
$pcgPython = Join-Path $project 'evolution\.venv\Scripts\python.exe'
$smokeConfig = Get-Content -Raw -Encoding utf8 -LiteralPath 'configs/shell_sampling_focused_smoke.json' | ConvertFrom-Json
$archiveRoot = $smokeConfig.output_root
$smoke = Join-Path $archiveRoot $smokeConfig.run_id
$baseline = Join-Path $archiveRoot 'shell_local_g20_pop8_20261125_143448_831'
if (-not (Test-Path -LiteralPath (Join-Path $smoke 'overview.json'))) {
    throw 'Finish the registered G0-G2 smoke run before starting the comparison.'
}

$arms = @('focused', 'random')
$jobs = @()
foreach ($arm in $arms) {
    $config = "configs/shell_sampling_${arm}_g20.json"
    $settings = Get-Content -LiteralPath $config -Raw -Encoding utf8 | ConvertFrom-Json
    $run = Join-Path $settings.output_root $settings.run_id
    if (Test-Path -LiteralPath (Join-Path $run 'overview.json')) {
        continue
    }
    $command = "-B -m full_pcg experiment --config $config"
    if (Test-Path -LiteralPath (Join-Path $run 'registration.json')) {
        $command += ' --resume'
    }
    $logPrefix = "$run.$(Get-Date -Format 'yyyyMMdd_HHmmss_fff')"
    $jobs += Start-Process -FilePath $pcgPython -WorkingDirectory $project -WindowStyle Hidden `
        -ArgumentList $command -RedirectStandardOutput "$logPrefix.out.log" `
        -RedirectStandardError "$logPrefix.err.log" -PassThru
    Write-Output "$arm archive: $run"
    Write-Output "$arm logs: $logPrefix"
}
foreach ($job in $jobs) {
    $job.WaitForExit()
}
if ($jobs | Where-Object { $_.ExitCode -ne 0 }) {
    throw 'A comparison arm exited with an error. See its logs and resume the registered run.'
}

$focused = Join-Path $archiveRoot 'shell_sampling_focused_g20_v1'
$random = Join-Path $archiveRoot 'shell_sampling_random_g20_v1'
foreach ($run in @($focused, $random)) {
    & $pcgPython -B -m full_pcg verify --run $run --workers 4
    if ($LASTEXITCODE -ne 0) {
        throw "Verification failed: $run"
    }
}
$report = Join-Path $archiveRoot 'shell_sampling_comparison_v1.json'
$markdown = Join-Path $archiveRoot 'shell_sampling_comparison_v1.md'
& $pcgPython -B -m full_pcg.viewer.sampling_report --baseline $baseline --focused $focused --random $random --output $report --markdown $markdown
if ($LASTEXITCODE -ne 0) {
    throw 'Comparison failed. Review the evidence or configuration mismatch.'
}
Write-Output "Comparison report: $report"
Write-Output "Readable report: $markdown"
