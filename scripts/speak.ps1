param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$Volume = 70,
    [string]$Voice = ""
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Volume = [Math]::Max(0, [Math]::Min(100, $Volume))
if ($Voice) {
    try { $synth.SelectVoice($Voice) } catch { }
}
$text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
if ($text) { $synth.Speak($text) }
