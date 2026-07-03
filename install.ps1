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
    [string]$Target,
    [switch]$Yes,
    [string]$Platform,
    [string]$Language,
    [string[]]$Mcp = @()
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

function Assert-NativeExit([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)." }
}

$MaikaRoot = $PSScriptRoot
$Venv = Join-Path $MaikaRoot '.venv'

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    throw "Target directory does not exist: $Target"
}
$Target = (Resolve-Path -LiteralPath $Target).Path

# Resolve a Python launcher (`python`, then `py -3`); require >= 3.9.
function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.9') { return @{ Exe = 'python'; Args = @() } }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $v = & py -3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.9') { return @{ Exe = 'py'; Args = @('-3') } }
    }
    return $null
}

$Py = Resolve-Python
if ($null -eq $Py) {
    throw "Python 3.9+ not found. Install Python and ensure 'python' or 'py' is on PATH."
}

# The write-gate hook invokes Python by name at runtime; pass the launcher we resolved
# so a `py`-only box doesn't get a bare `python` command that can't launch.
$HookPython = if ($Py.Args.Count -gt 0) { "$($Py.Exe) $($Py.Args -join ' ')" } else { $Py.Exe }

$VenvPy  = Join-Path $Venv 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Venv)) {
    Write-Host "-> Creating virtualenv at $Venv"
    try {
        & $Py.Exe @($Py.Args) -m venv $Venv
        Assert-NativeExit "venv creation"
        & $VenvPy -m pip install --quiet --upgrade pip
        Assert-NativeExit "pip upgrade"
        & $VenvPy -m pip install --quiet "jinja2>=3.1" "pyyaml>=6.0"
        Assert-NativeExit "dependency install"
    } catch {
        # A half-built venv makes every future run skip dependency install.
        if (Test-Path -LiteralPath $Venv) { Remove-Item -Recurse -Force -LiteralPath $Venv }
        throw
    }
}

# Install the maika CLI as an editable package (creates .venv\Scripts\maika.exe).
& $VenvPy -m pip install --quiet -e $MaikaRoot
Assert-NativeExit "maika editable install"

# Expose `maika` on PATH via a shim (Windows symlinks need admin/dev-mode).
$BinDir = Join-Path $env:LOCALAPPDATA 'Maika\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$MaikaExe = Join-Path $Venv 'Scripts\maika.exe'
$Shim = Join-Path $BinDir 'maika.cmd'
# ASCII shim + non-ASCII clone path can corrupt the target. Fall back to the
# DOS 8.3 short path, which is pure ASCII by construction.
$ShimTarget = $MaikaExe
if ($ShimTarget -match '[^\x00-\x7F]') {
    try {
        $Fso = New-Object -ComObject Scripting.FileSystemObject
        $ShimTarget = $Fso.GetFile($MaikaExe).ShortPath
    } catch {
        Write-Warning "Could not resolve an 8.3 short path for $MaikaExe."
    }
    if ($ShimTarget -match '[^\x00-\x7F]') {
        Write-Warning "Install path contains non-ASCII characters and 8.3 names are unavailable; the 'maika' shim may not work. Clone Maika under an ASCII-only path to fix."
    }
}
Set-Content -LiteralPath $Shim -Value "@echo off`r`n`"$ShimTarget`" %*" -Encoding ASCII
Write-Host "-> Installed 'maika' shim -> $Shim"

# Append to user PATH via the registry API: read RAW (unexpanded) value and
# preserve the value kind, so REG_EXPAND_SZ entries like %JAVA_HOME%\bin survive.
$EnvKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
try {
    $RawPath = [string]$EnvKey.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    $Kind = if ($EnvKey.GetValueNames() -contains 'Path') { $EnvKey.GetValueKind('Path') } else { [Microsoft.Win32.RegistryValueKind]::ExpandString }
    $Segments = $RawPath -split ';' | Where-Object { $_ -ne '' }
    if ($Segments -notcontains $BinDir) {
        $NewPath = if ([string]::IsNullOrEmpty($RawPath)) { $BinDir } else { "$RawPath;$BinDir" }
        $EnvKey.SetValue('Path', $NewPath, $Kind)
        Write-Host "-> Added $BinDir to your user PATH. Open a new terminal to use 'maika'."
    }
} finally {
    $EnvKey.Close()
}

# The write-gate hook runs OUTSIDE the venv via the resolved launcher; a clean
# Windows Python has no pyyaml, which would silently kill the gate at runtime.
& $Py.Exe @($Py.Args) -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Hook interpreter ($HookPython) lacks 'pyyaml' - installing (pip --user)."
    & $Py.Exe @($Py.Args) -m pip install --user --quiet pyyaml
    & $Py.Exe @($Py.Args) -c "import yaml" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not install 'pyyaml' for $HookPython. The write-gate hook WILL FAIL. Run: $HookPython -m pip install --user pyyaml"
    }
}

# Route to update if Maika already installed, else init.
$Configs = @(
    (Join-Path $Target '.agents\resolved-config.yaml'),
    (Join-Path $Target '.claude\resolved-config.yaml'),
    (Join-Path $Target '.maika\resolved-config.yaml')
)
$Existing = $Configs | Where-Object { Test-Path -LiteralPath $_ }

$ScaffoldArgs = @('--target', $Target, '--hook-python', $HookPython)
if ($Yes) { $ScaffoldArgs += '--yes' }
if ($Platform) { $ScaffoldArgs += @('--platform', $Platform) }
if ($Language) { $ScaffoldArgs += @('--language', $Language) }
foreach ($m in $Mcp) { $ScaffoldArgs += @('--mcp', $m) }

Push-Location $MaikaRoot
try {
    if ($Existing) {
        Write-Host "-> Existing Maika install detected — updating."
        & $VenvPy -m cli.maika update --target $Target --hook-python $HookPython
        if ($LASTEXITCODE -ne 0) { throw "cli.maika update failed (exit $LASTEXITCODE)." }
    } else {
        Write-Host "-> Fresh install."
        & $VenvPy -m cli.maika init @ScaffoldArgs
        if ($LASTEXITCODE -ne 0) { throw "cli.maika init failed (exit $LASTEXITCODE)." }
    }
} finally {
    Pop-Location
}
