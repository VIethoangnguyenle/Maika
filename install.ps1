#Requires -Version 5.1
<#
.SYNOPSIS
  Maika installer for Windows — bootstrap a venv and scaffold/update Maika into a target project.
.EXAMPLE
  .\install.ps1 C:\path\to\your\project
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target
)

$ErrorActionPreference = 'Stop'

$MaikaRoot = $PSScriptRoot
$Venv = Join-Path $MaikaRoot '.venv'

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    throw "Target directory does not exist: $Target"
}
$Target = (Resolve-Path -LiteralPath $Target).Path

# Resolve a Python launcher (`python`, then `py -3`); require >= 3.8.
function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.8') { return @{ Exe = 'python'; Args = @() } }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $v = & py -3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.8') { return @{ Exe = 'py'; Args = @('-3') } }
    }
    return $null
}

$Py = Resolve-Python
if ($null -eq $Py) {
    throw "Python 3.8+ not found. Install Python and ensure 'python' or 'py' is on PATH."
}

$VenvPy  = Join-Path $Venv 'Scripts\python.exe'
$VenvPip = Join-Path $Venv 'Scripts\pip.exe'

if (-not (Test-Path -LiteralPath $Venv)) {
    Write-Host "-> Creating virtualenv at $Venv"
    & $Py.Exe @($Py.Args) -m venv $Venv
    & $VenvPip install --quiet --upgrade pip
    & $VenvPip install --quiet "jinja2>=3.1" "pyyaml>=6.0"
}

# Install the maika CLI as an editable package (creates .venv\Scripts\maika.exe).
& $VenvPip install --quiet -e $MaikaRoot

# Expose `maika` on PATH via a shim (Windows symlinks need admin/dev-mode).
$BinDir = Join-Path $env:LOCALAPPDATA 'Maika\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$MaikaExe = Join-Path $Venv 'Scripts\maika.exe'
$Shim = Join-Path $BinDir 'maika.cmd'
Set-Content -LiteralPath $Shim -Value "@echo off`r`n`"$MaikaExe`" %*" -Encoding ASCII
Write-Host "-> Installed 'maika' shim -> $Shim"

$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$UserPath;$BinDir", 'User')
    Write-Host "-> Added $BinDir to your user PATH. Open a new terminal to use 'maika'."
}

# The write-gate hook runs OUTSIDE the venv via system `python`; warn if it lacks pyyaml.
& $Py.Exe @($Py.Args) -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "System Python lacks 'pyyaml'; the write-gate hook needs it. Run: $($Py.Exe) -m pip install pyyaml"
}

# Route to update if Maika already installed, else init.
$Configs = @(
    (Join-Path $Target '.agents\resolved-config.yaml'),
    (Join-Path $Target '.claude\resolved-config.yaml'),
    (Join-Path $Target '.maika\resolved-config.yaml')
)
$Existing = $Configs | Where-Object { Test-Path -LiteralPath $_ }

Push-Location $MaikaRoot
try {
    if ($Existing) {
        Write-Host "-> Existing Maika install detected — updating."
        & $VenvPy -m cli.maika update --target $Target
        if ($LASTEXITCODE -ne 0) { throw "cli.maika update failed (exit $LASTEXITCODE)." }
    } else {
        Write-Host "-> Fresh install."
        & $VenvPy -m cli.maika init --target $Target
        if ($LASTEXITCODE -ne 0) { throw "cli.maika init failed (exit $LASTEXITCODE)." }
    }
} finally {
    Pop-Location
}
