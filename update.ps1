[CmdletBinding()]
param(
    [ValidateSet("Auto", "Codex", "Generic", "All")]
    [string]$Target = "Auto",
    [switch]$SkipPull,
    [string]$CodexHome,
    [string]$GenericHome
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$GitDir = Join-Path $RepoRoot ".git"

if (-not $SkipPull -and (Test-Path -LiteralPath $GitDir -PathType Container)) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        throw "Git repository detected, but git is not available. Use -SkipPull to update from the current checkout."
    }
    $dirty = & $git.Source -C $RepoRoot status --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect Git worktree."
    }
    if ($dirty) {
        throw "The distribution repository has local changes. Commit or preserve them before updating."
    }
    $upstream = & $git.Source -C $RepoRoot rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $upstream) {
        & $git.Source -C $RepoRoot pull --ff-only
        if ($LASTEXITCODE -ne 0) {
            throw "git pull --ff-only failed. Existing installed skills were not changed."
        }
    } else {
        Write-Host "No Git upstream is configured; updating from the current checkout."
    }
}

$installParams = @{
    Target = $Target
    Force = $true
}
if ($CodexHome) { $installParams.CodexHome = $CodexHome }
if ($GenericHome) { $installParams.GenericHome = $GenericHome }

& (Join-Path $RepoRoot "install.ps1") @installParams

Write-Host "Update complete. Existing personal review data was not modified."
