# Install Grok Assistant on this PC: a venv, the program, and a shortcut.
param(
    [string]$Destination = $(Join-Path $env:LOCALAPPDATA "GrokAssistant"),
    [string]$Source = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$NoShortcuts,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @(
        @{ Command = "py"; Args = @("-3", "-c", "import sys; print(sys.executable)") },
        @{ Command = "python"; Args = @("-c", "import sys; print(sys.executable)") }
    )
    foreach ($item in $candidates) {
        $exe = Get-Command $item.Command -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        $path = & $item.Command @($item.Args) 2>$null
        if (-not $path) { continue }
        $version = & $path -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
        $parts = $version.Split(".")
        if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11)) {
            return $path.Trim()
        }
    }
    throw "Python 3.11 or newer is required. Install it from python.org and run this again."
}

if ((Test-Path $Destination) -and -not $Force) {
    $existing = Join-Path $Destination "venv\Scripts\python.exe"
    if (Test-Path $existing) {
        throw "Already installed at $Destination. Run again with -Force to replace it."
    }
}

$python = Find-Python
Write-Host "Python: $python"
Write-Host "From:   $Source"
Write-Host "To:     $Destination"

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$app = Join-Path $Destination "app"
if (Test-Path $app) { Remove-Item -Recurse -Force $app }
New-Item -ItemType Directory -Force -Path $app | Out-Null

$keep = @("src", "scripts", "listeners", "docs", "installer", "pyproject.toml", "requirements.txt", "README.md")
foreach ($name in $keep) {
    $from = Join-Path $Source $name
    if (-not (Test-Path $from)) { continue }
    Copy-Item -Path $from -Destination (Join-Path $app $name) -Recurse -Force
}

Get-ChildItem -Path $app -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

$venv = Join-Path $Destination "venv"
if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
& $python -m venv $venv
$venvPython = Join-Path $venv "Scripts\python.exe"
$venvPythonw = Join-Path $venv "Scripts\pythonw.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e $app
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

$check = & $venvPython -c "import grok_assistant; print(grok_assistant.__version__)"
if ($LASTEXITCODE -ne 0) { throw "The installed program does not import." }
Write-Host "Imported grok_assistant $check"

$icon = Join-Path $app "docs\img\grok.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$start = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$links = @((Join-Path $Destination "Grok Assistant.lnk"))
if (-not $NoShortcuts) {
    $links += (Join-Path $desktop "Grok Assistant.lnk")
    $links += (Join-Path $start "Grok Assistant.lnk")
}

$shell = New-Object -ComObject WScript.Shell
foreach ($linkPath in $links) {
    $shortcut = $shell.CreateShortcut($linkPath)
    $shortcut.TargetPath = $venvPythonw
    $shortcut.Arguments = "-m grok_assistant"
    $shortcut.WorkingDirectory = $app
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Grok Assistant"
    if (Test-Path $icon) { $shortcut.IconLocation = $icon }
    $shortcut.Save()
    Write-Host "Shortcut: $linkPath"
}

$uninstall = Join-Path $Destination "uninstall.ps1"
@"
`$ErrorActionPreference = 'Stop'
Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { `$_.Path -like '$venv*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item -Force -ErrorAction SilentlyContinue '$desktop\Grok Assistant.lnk'
Remove-Item -Force -ErrorAction SilentlyContinue '$start\Grok Assistant.lnk'
Remove-Item -Recurse -Force '$Destination'
Write-Host 'Grok Assistant removed.'
"@ | Set-Content -Path $uninstall -Encoding UTF8

Write-Host "Installed. Launch: $venvPythonw -m grok_assistant"
