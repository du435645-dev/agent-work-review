[CmdletBinding()]
param(
    [ValidateSet("Auto", "Codex", "Generic", "All")]
    [string]$Target = "Auto",
    [string]$PersonId,
    [switch]$Force,
    [string]$CodexHome,
    [string]$GenericHome
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$SourceSkills = Join-Path $RepoRoot "skills"
$SkillNames = @("work-review-ppt-summary", "guizang-ppt-skill")
$VersionFile = Join-Path $RepoRoot "version.json"

if (-not $CodexHome) {
    $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
}
if (-not $GenericHome) {
    $GenericHome = Join-Path $HOME ".work-review"
}

$CodexHome = [System.IO.Path]::GetFullPath($CodexHome)
$GenericHome = [System.IO.Path]::GetFullPath($GenericHome)
$BackupRoot = Join-Path $GenericHome ("backups\" + (Get-Date -Format "yyyyMMdd_HHmmss_fff"))

function Assert-DistributionSources {
    foreach ($name in $SkillNames) {
        $skillRoot = Join-Path $SourceSkills $name
        if (-not (Test-Path -LiteralPath (Join-Path $skillRoot "SKILL.md") -PathType Leaf)) {
            throw "Missing distributable skill: $skillRoot"
        }
    }
}

function Assert-SafeSkillPath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$SkillsRoot,
        [Parameter(Mandatory)] [string]$SkillName
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $resolvedRoot = [System.IO.Path]::GetFullPath($SkillsRoot).TrimEnd('\') + '\'
    if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside skills root: $resolvedPath"
    }
    if ([System.IO.Path]::GetFileName($resolvedPath) -ne $SkillName) {
        throw "Unexpected destination leaf: $resolvedPath"
    }
}

function Install-SkillSet {
    param(
        [Parameter(Mandatory)] [string]$SkillsRoot,
        [Parameter(Mandatory)] [string]$TargetName
    )

    New-Item -ItemType Directory -Force -Path $SkillsRoot | Out-Null
    foreach ($name in $SkillNames) {
        $source = Join-Path $SourceSkills $name
        $destination = Join-Path $SkillsRoot $name
        Assert-SafeSkillPath -Path $destination -SkillsRoot $SkillsRoot -SkillName $name

        if (Test-Path -LiteralPath $destination) {
            if (-not $Force) {
                throw "$destination already exists. Run update.ps1 or install.ps1 -Force."
            }
            $backup = Join-Path $BackupRoot (Join-Path $TargetName $name)
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
            Copy-Item -LiteralPath $destination -Destination $backup -Recurse -Force
            Remove-Item -LiteralPath $destination -Recurse -Force
        }

        Copy-Item -LiteralPath $source -Destination $SkillsRoot -Recurse -Force
        Write-Host "Installed $name -> $destination"
    }
}

Assert-DistributionSources

$Targets = @()
$GenericSkills = Join-Path $GenericHome "skills"
$CodexSkills = Join-Path $CodexHome "skills"

switch ($Target) {
    "Generic" { $Targets += [pscustomobject]@{ Name = "generic"; SkillsRoot = $GenericSkills } }
    "Codex" { $Targets += [pscustomobject]@{ Name = "codex"; SkillsRoot = $CodexSkills } }
    "All" {
        $Targets += [pscustomobject]@{ Name = "generic"; SkillsRoot = $GenericSkills }
        $Targets += [pscustomobject]@{ Name = "codex"; SkillsRoot = $CodexSkills }
    }
    "Auto" {
        $Targets += [pscustomobject]@{ Name = "generic"; SkillsRoot = $GenericSkills }
        if (Test-Path -LiteralPath $CodexHome) {
            $Targets += [pscustomobject]@{ Name = "codex"; SkillsRoot = $CodexSkills }
        }
    }
}

foreach ($item in $Targets) {
    Install-SkillSet -SkillsRoot $item.SkillsRoot -TargetName $item.Name
}

New-Item -ItemType Directory -Force -Path $GenericHome | Out-Null
$version = if (Test-Path -LiteralPath $VersionFile) {
    (Get-Content -Raw -LiteralPath $VersionFile | ConvertFrom-Json).version
} else {
    "unknown"
}
$manifest = [ordered]@{
    version = $version
    installed_at = (Get-Date).ToString("o")
    source = $RepoRoot
    targets = @($Targets | ForEach-Object { $_.SkillsRoot })
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $GenericHome "install-manifest.json") -Encoding utf8

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python is required to initialize local review data. Skills were installed, but data initialization did not run."
}
$initializer = Join-Path $GenericSkills "work-review-ppt-summary\scripts\init_local_review.py"
if (-not (Test-Path -LiteralPath $initializer)) {
    $initializer = Join-Path $CodexSkills "work-review-ppt-summary\scripts\init_local_review.py"
}
$initArgs = @("-X", "utf8", $initializer, "--root", (Join-Path $GenericHome "data"))
if ($PersonId) {
    $initArgs += @("--person-id", $PersonId)
}
& $python.Source @initArgs
if ($LASTEXITCODE -ne 0) {
    throw "Local data initialization failed with exit code $LASTEXITCODE."
}

Write-Host "Installation complete. Personal data remains under $GenericHome\data and is never copied into the distribution repository."
