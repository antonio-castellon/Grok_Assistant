param(
    [string]$Culture = "es-ES",
    [string]$PauseFile = "",
    [switch]$Probe
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
try {
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($Culture)
} catch {
    [Console]::Out.WriteLine("ERR:no-recognizer")
    [Console]::Out.Flush()
    exit 2
}
if ($Probe) {
    [Console]::Out.WriteLine("READY")
    [Console]::Out.Flush()
    exit 0
}
try {
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $engine.SetInputToDefaultAudioDevice()
} catch {
    [Console]::Out.WriteLine("ERR:no-microphone")
    [Console]::Out.Flush()
    exit 3
}
$engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(3500)
$engine.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(3500)
$engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds(2)
[Console]::Out.WriteLine("READY")
[Console]::Out.Flush()
while ($true) {
    if ($PauseFile -and (Test-Path -LiteralPath $PauseFile)) {
        Start-Sleep -Milliseconds 200
        continue
    }
    $result = $engine.Recognize()
    if ($result -and $result.Text) {
        [Console]::Out.WriteLine("LINE:" + $result.Text)
        [Console]::Out.Flush()
    }
}
