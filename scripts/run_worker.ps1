param(
    [int]$Port = 9998,
    [int]$Procs = 0,
    [double]$Slowdown = 1.0,
    [int]$CrashAfter = 0
)

$workerArgs = @("--port", $Port, "--procs", $Procs, "--slowdown", $Slowdown)
if ($CrashAfter -gt 0) {
    $workerArgs += @("--crash-after", $CrashAfter)
}

python (Join-Path $PSScriptRoot "..\worker_sort.py") @workerArgs
