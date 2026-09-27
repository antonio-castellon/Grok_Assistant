# Build the single GrokAssistant.exe. This is for making the program, not for installing it.
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
$python = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        if ($candidate -eq "py") {
            $python = & py -3 -c "import sys; print(sys.executable)"
        } else {
            $python = & python -c "import sys; print(sys.executable)"
        }
        break
    }
}
if (-not $python) { throw "Python 3.11 or newer is required to build the executable." }
& $python -m pip install --upgrade pip pyinstaller pystray Pillow "sherpa-onnx==1.13.8" "sounddevice==0.5.6" "numpy>=2.2,<2.5"
& $python -m PyInstaller --noconfirm --clean (Join-Path $root "GrokAssistant.spec")
$exe = Join-Path $root "dist\GrokAssistant.exe"
if (-not (Test-Path $exe)) { throw "The executable was not created." }
Write-Host "Built $exe"
