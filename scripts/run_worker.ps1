param(
    [int]$Port = 9998,
    [int]$Procs = 0,
    [double]$Slowdown = 1.0,
    [int]$CrashAfter = 0
)

$root = Split-Path -Parent $PSScriptRoot
$workerArgs = @("--port", $Port, "--procs", $Procs, "--slowdown", $Slowdown)
if ($CrashAfter -gt 0) {
    $workerArgs += @("--crash-after", $CrashAfter)
}

Push-Location $root
try {
    python -m src.worker_sort @workerArgs
}
finally {
    Pop-Location
}
