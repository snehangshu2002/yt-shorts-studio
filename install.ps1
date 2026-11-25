# Install the yt-shorts-studio skill for every AI coding agent found on this machine (Windows).
#   .\install.ps1                    auto-detect agents (always also installs to ~\.agents\skills)
#   .\install.ps1 -Agent codex       one agent: claude | codex | antigravity | agents | all
#   .\install.ps1 -Project D:\proj   install into a project (D:\proj\.agents\skills + .claude\skills)
#   .\install.ps1 -Deps              also pip-install the Python dependencies
param(
    [string]$Agent = "auto",
    [string]$Project = "",
    [switch]$Deps
)
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills\yt-shorts-studio"
$name = "yt-shorts-studio"
$H = $env:USERPROFILE
$targets = @()

function Want($key, $dir) {
    return ($Agent -eq "all") -or ($Agent -eq $key) -or (($Agent -eq "auto") -and (Test-Path $dir))
}

if ($Project) {
    $targets += (Join-Path $Project ".agents\skills"), (Join-Path $Project ".claude\skills")
} else {
    if (Want "claude" "$H\.claude") { $targets += "$H\.claude\skills" }
    if (Want "codex" "$H\.codex") { $targets += "$H\.codex\skills" }
    if (Want "antigravity" "$H\.gemini") { $targets += "$H\.gemini\config\skills", "$H\.gemini\antigravity\skills" }
    if (@("auto", "all", "agents", "codex") -contains $Agent) { $targets += "$H\.agents\skills" }
}

foreach ($t in $targets) {
    New-Item -ItemType Directory -Force $t | Out-Null
    $dest = Join-Path $t $name
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Copy-Item -Recurse $src $dest
    $cache = Join-Path $dest "scripts\__pycache__"
    if (Test-Path $cache) { Remove-Item -Recurse -Force $cache }
    Write-Output "installed -> $dest"
}

if ($Deps) { python -m pip install --user -r (Join-Path $PSScriptRoot "requirements.txt") }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Output "note: ffmpeg not found on PATH (needed for cutting and rendering)"
}
Write-Output "Restart your agent so it picks up the new skill."
