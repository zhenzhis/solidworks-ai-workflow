param(
    [string]$Python = '3.13',
    [switch]$Development,
    [switch]$WithDocumentation
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and run this script again.'
}
Push-Location $repoRoot
try {
    $syncArgs = @('sync','--frozen','--python',$Python,'--extra','cad','--extra','mcp')
    if ($Development) { $syncArgs += @('--extra','test') }
    & uv @syncArgs
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    $pythonExe = Join-Path $repoRoot '.venv/Scripts/python.exe'
    $configureArgs = @('-X','utf8','-B','scripts/configure.py')
    if ($WithDocumentation) { $configureArgs += '--with-docs' }
    & $pythonExe @configureArgs
    if ($LASTEXITCODE -ne 0) { throw 'Project configuration failed; existing files were preserved.' }
    & $pythonExe -X utf8 -B -m sw_workflow.cli doctor
    if ($LASTEXITCODE -ne 0) { throw 'Doctor failed.' }
    Write-Host 'Ready. Open this repository as a trusted Codex project; then use the project skill or CLI.'
}
finally { Pop-Location }
