param(
    [string]$Culture = "es-ES",
    [string]$PauseFile = "",
    [string]$ScoreDir = "",
    [switch]$Probe
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
# The string constructor wants a recognizer id such as MS-3082-80-DESK, not a culture name.
try {
    $cultureInfo = [System.Globalization.CultureInfo]::new($Culture)
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($cultureInfo)
} catch {
    $info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() |
        Where-Object { $_.Culture.Name -eq $Culture } |
        Select-Object -First 1
    if (-not $info) {
        [Console]::Out.WriteLine("ERR:no-recognizer")
        [Console]::Out.Flush()
        exit 2
    }
    try {
        $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($info)
    } catch {
        [Console]::Out.WriteLine("ERR:no-recognizer")
        [Console]::Out.Flush()
        exit 2
    }
}
if ($Probe) {
    [Console]::Out.WriteLine("READY")
    [Console]::Out.Flush()
    exit 0
}
if ($ScoreDir) {
    try {
        $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    } catch {
        [Console]::Out.WriteLine("ERR:no-recognizer")
        [Console]::Out.Flush()
        exit 2
    }
    Get-ChildItem -LiteralPath $ScoreDir -Filter *.wav | Sort-Object Name | ForEach-Object {
        $text = ""
        try {
            $engine.SetInputToWaveFile($_.FullName)
            $result = $engine.Recognize()
            if ($result -and $result.Text) { $text = $result.Text }
        } catch {
            $text = ""
        }
        [Console]::Out.WriteLine("LINE:" + $_.Name + "|" + $text)
        [Console]::Out.Flush()
    }
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
$engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(1200)
$engine.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(1200)
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
