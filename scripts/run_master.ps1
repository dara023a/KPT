param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("seq", "local", "dist", "bench")]
    [string]$Mode,

    [string]$Size = "10m",
    [string]$Hosts = "",
    [int]$Repeat = 0,
    [string]$Dataset = "",
    [string]$Suite = "scalability"
)

$root = Split-Path -Parent $PSScriptRoot
$masterArgs = @($Mode, "--size", $Size)
if ($Hosts) { $masterArgs += @("--hosts", $Hosts) }
if ($Repeat -gt 0) { $masterArgs += @("--repeat", $Repeat) }
if ($Dataset) { $masterArgs += @("--dataset", $Dataset) }
if ($Mode -eq "bench") { $masterArgs += @("--suite", $Suite) }

Push-Location $root
try {
    python -m src.master_sort @masterArgs
}
finally {
    Pop-Location
}
