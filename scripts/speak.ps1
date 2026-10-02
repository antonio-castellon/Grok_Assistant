param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$Volume = 70,
    [string]$Voice = "",
    [string]$Wav = ""
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.Volume = [Math]::Max(0, [Math]::Min(100, $Volume))
    if ($Voice) {
        try { $synth.SelectVoice($Voice) } catch { }
    }
    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if (-not $text) { return }
    if ($Wav) { $synth.SetOutputToWaveFile($Wav) }
    $synth.Speak($text)
} finally {
    $synth.Dispose()
}
