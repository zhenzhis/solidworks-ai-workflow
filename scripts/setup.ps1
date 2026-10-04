param(
    [string]$Python = '3.13',
    [switch]$Development,
    [switch]$WithDocumentation,
    [switch]$VerifyCad
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and run this script again.'
}
Push-Location $repoRoot
$previousUvEnvironment = $env:UV_PROJECT_ENVIRONMENT
try {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $repoRoot '.venv'
    $syncArgs = @('sync','--frozen','--python',$Python,'--extra','cad','--extra','mcp')
    if ($Development) { $syncArgs += @('--extra','test') }
    & uv @syncArgs
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    $pythonExe = Join-Path $repoRoot '.venv/Scripts/python.exe'
    $configureArgs = @('-X','utf8','-B','scripts/install.py')
    if ($WithDocumentation) { $configureArgs += '--with-docs' }
    if ($VerifyCad) { $configureArgs += '--verify-cad' }
    & $pythonExe @configureArgs
    if ($LASTEXITCODE -ne 0) { throw 'Installation verification failed. Inspect .local/install-report.json; no success is claimed.' }
    Write-Host 'Verified installation status is recorded in .local/install-report.json. Open and trust this project in Codex to activate its Skill and MCP.'
}
finally {
    $env:UV_PROJECT_ENVIRONMENT = $previousUvEnvironment
    Pop-Location
}
