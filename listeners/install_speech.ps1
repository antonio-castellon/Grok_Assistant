param(
    [Parameter(Mandatory = $true)]
    [string]$Log
)
$ErrorActionPreference = "Stop"
try {
    $name = "Language.Speech~~~es-ES~0.0.1.0"
    $cap = Get-WindowsCapability -Online | Where-Object { $_.Name -eq $name } | Select-Object -First 1
    if (-not $cap) {
        throw "Windows no ofrece el idioma de voz es-ES en este equipo."
    }
    if ($cap.State -ne "Installed") {
        Add-WindowsCapability -Online -Name $name | Out-Null
    }
    Set-Content -LiteralPath $Log -Value "OK" -Encoding utf8
} catch {
    Set-Content -LiteralPath $Log -Value ("ERR:" + $_.Exception.Message) -Encoding utf8
    exit 1
}
