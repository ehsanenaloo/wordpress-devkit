[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('claude','codex','antigravity')][string]$Agent,
    [string]$Destination,
    [switch]$Replace,
    [string[]]$Skill,
    [switch]$Preview,
    [switch]$Status,
    [switch]$Uninstall,
    [switch]$Confirm,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$installerArgs = @((Join-Path $PSScriptRoot 'install.py'), '--agent', $Agent)
if ($Destination) {
    # A trailing separator would swallow the closing quote in Windows PowerShell 5.1.
    $trimmed = $Destination.TrimEnd('\', '/')
    if ($trimmed -and $trimmed -notmatch '^[A-Za-z]:$') { $Destination = $trimmed }
    $installerArgs += @('--destination', $Destination)
}
if ($Replace) { $installerArgs += '--replace' }
# -File invocations pass 'a,b' as one string; accept both forms.
foreach ($skillName in @($Skill | ForEach-Object { $_ -split ',' } | Where-Object { $_ })) { $installerArgs += @('--skill', $skillName.Trim()) }
if ($Preview) { $installerArgs += '--preview' }
if ($Status) { $installerArgs += '--status' }
if ($Uninstall) { $installerArgs += '--uninstall' }
if ($Confirm) { $installerArgs += '--confirm' }
if ($Force) { $installerArgs += '--force' }
function Test-Python([string]$Command, [string[]]$Prefix) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { return $false }
    # The Microsoft Store alias exits non-zero without running Python.
    & $Command @Prefix --version *> $null
    return ($LASTEXITCODE -eq 0)
}
if (Test-Python 'py' @('-3')) {
    & py -3 @installerArgs
} elseif (Test-Python 'python' @()) {
    & python @installerArgs
} elseif (Test-Python 'python3' @()) {
    & python3 @installerArgs
} else {
    [Console]::Error.WriteLine('Python 3 is required for the installer.')
    exit 1
}
exit $LASTEXITCODE
