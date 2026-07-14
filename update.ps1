$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
if (Test-Path -LiteralPath (Join-Path $repo ".git")) {
    $dirty = git -C $repo status --porcelain
    if ($dirty) { throw "The checkout has local changes. Preserve them before updating." }
    git -C $repo pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "git pull --ff-only failed." }
}
& (Join-Path $repo "install.ps1") @args
exit $LASTEXITCODE
