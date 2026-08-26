#requires -Version 5.1
<#
.SYNOPSIS
  Sincroniza personal_samples y deja el trainer listo para mariano.

.DESCRIPTION
  Copia WAV a $HOME\mww-data\personal_samples, arranca el contenedor Docker
  y muestra la UI en :8789 para Start training.

  En AMD Radeon RX 6750 XT usa -Cpu (sin --gpus all). CUDA no aplica.
#>
[CmdletBinding()]
param(
    [switch]$Cpu,
    [switch]$Blackwell,
    [switch]$DryRun,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$WakeWord = "mariano"
$RecPort = if ($env:REC_PORT) { $env:REC_PORT } else { "8789" }
$ContainerName = if ($env:MWW_NVIDIA_CONTAINER) { $env:MWW_NVIDIA_CONTAINER } else { "waynelab-mww-trainer" }
$DataDir = if ($env:MWW_NVIDIA_DATA_DIR) { $env:MWW_NVIDIA_DATA_DIR } else { Join-Path $HOME "mww-data" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoSamples = Join-Path $ScriptDir "personal_samples"

function Write-Log {
    param([string]$Message)
    Write-Host "[train-mariano-windows] $Message"
}

if ($Help) {
    @"
Uso: .\train_mariano_windows.ps1 [-Cpu] [-Blackwell] [-DryRun] [-Help]

Sincroniza personal_samples y abre el flujo de entrenamiento mariano en :$RecPort.
Si el contenedor no existe, delega en setup_trainer_windows.ps1.

  -Cpu   PC AMD / sin NVIDIA (RX 6750 XT). Pasa -Cpu al setup.
"@
    exit 0
}

if ($Blackwell -and $Cpu) {
    throw "-Blackwell no se combina con -Cpu"
}

$personalDest = Join-Path $DataDir "personal_samples"
New-Item -ItemType Directory -Force -Path $personalDest | Out-Null

$candidates = @()
if ($env:MWW_PERSONAL_SRC) { $candidates += $env:MWW_PERSONAL_SRC }
$candidates += $RepoSamples
$copied = 0
foreach ($src in $candidates) {
    if (-not (Test-Path $src)) { continue }
    $wavs = Get-ChildItem -Path $src -File -Filter *.wav -ErrorAction SilentlyContinue
    if (-not $wavs) { continue }
    foreach ($wav in $wavs) {
        Copy-Item $wav.FullName -Destination (Join-Path $personalDest $wav.Name) -Force
        $copied++
    }
    Write-Log "personal_samples: $copied WAV copiados desde $src -> $personalDest"
    break
}
if ($copied -eq 0) {
    Write-Log "Sin WAV locales. Copia la carpeta personal_samples del Mac a $RepoSamples"
}

Write-Log "Wake word=$WakeWord UI=http://127.0.0.1:$RecPort DATA_DIR=$DataDir"

if ($DryRun) {
    Write-Log "dry-run: docker start $ContainerName"
    Write-Log "Abre http://127.0.0.1:$RecPort -> Trainer -> mariano / Spanish -> Start training"
    exit 0
}

$setup = Join-Path $ScriptDir "setup_trainer_windows.ps1"
$existing = $null
try {
    $existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
} catch {
    Write-Log "docker no disponible — ejecuta primero setup_trainer_windows.ps1"
    throw
}

if ($existing) {
    docker start $ContainerName | Out-Null
    Write-Log "Contenedor $ContainerName en marcha"
} else {
    Write-Log "Contenedor ausente — llamando setup_trainer_windows.ps1"
    $setupArgs = @()
    if ($Cpu) { $setupArgs += "-Cpu" }
    if ($Blackwell) { $setupArgs += "-Blackwell" }
    & $setup @setupArgs
}

Write-Log "Abre http://127.0.0.1:$RecPort"
Write-Log "Trainer -> wake word=mariano -> language=Spanish -> revisa personal_samples -> Start training"
Write-Log "Modelo: $DataDir\trained_wake_words\mariano.tflite"
