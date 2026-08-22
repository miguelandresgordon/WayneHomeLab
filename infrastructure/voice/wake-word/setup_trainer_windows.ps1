#requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap del trainer microWakeWord en Windows 11 (CPU o NVIDIA).

.DESCRIPTION
  TensorFlow+CUDA no es el camino nativo en Windows. Este script prepara
  Docker Desktop (WSL2) + la imagen ghcr.io/tatertotterson/microwakeword
  y copia personal_samples al volumen /data.

  En el PC WayneHomeLab (AMD Ryzen 5 3600 + Radeon RX 6750 XT) CUDA no aplica:
  usa -Cpu (omite --gpus all). La misma imagen Tater corre en CPU.
  -Blackwell es solo para RTX 50-series NVIDIA.

.PARAMETER Cpu
  No pasa --gpus all. Obligatorio en AMD Radeon (RX 6750 XT) o si no hay NVIDIA.

.PARAMETER Blackwell
  Usa la imagen RTX 50-series (CUDA 12.8 / sm_120). Incompatible con -Cpu.

.PARAMETER DryRun
  Imprime los comandos docker sin ejecutarlos.

.PARAMETER Help
  Muestra la ayuda.
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
$Image = if ($Blackwell) {
    "ghcr.io/tatertotterson/microwakeword:blackwell"
} else {
    "ghcr.io/tatertotterson/microwakeword:latest"
}
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoSamples = Join-Path $ScriptDir "personal_samples"

function Write-Log {
    param([string]$Message)
    Write-Host "[setup-trainer-windows] $Message"
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-TrainerGpuKind {
    if (Test-Command "nvidia-smi") {
        return "nvidia"
    }
    try {
        foreach ($g in @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)) {
            $name = [string]$g.Name
            if ($name -match "NVIDIA") { return "nvidia" }
            if ($name -match "AMD|Radeon") { return "amd" }
        }
    } catch {
        return "unknown"
    }
    return "unknown"
}

function Show-Help {
    @"
Uso: .\setup_trainer_windows.ps1 [-Cpu] [-Blackwell] [-DryRun] [-Help]

Prepara Docker Desktop + WSL2 para entrenar la wake word mariano.

  -Cpu         Omite --gpus all. Usar en AMD Radeon RX 6750 XT / sin NVIDIA.
  -Blackwell   Imagen RTX 50-series (ghcr.io/tatertotterson/microwakeword:blackwell)
  -DryRun      Imprime docker pull/run, no ejecuta
  -Help        Esta ayuda

Requisitos Windows 11 (este lab):
  1. WSL2 (wsl --install si falta; reiniciar)
  2. Docker Desktop con backend WSL2
  3. >= 80 GB libres (TTS + negativos la primera vez)
  4. GPU NVIDIA opcional. RX 6750 XT = CUDA no aplica -> -Cpu

Si nvidia-smi no existe, el script elige CPU aunque no pases -Cpu.

Variables:
  MWW_NVIDIA_DATA_DIR   default: $HOME\mww-data  (se monta en /data)
  MWW_PERSONAL_SRC      carpeta extra de WAV a copiar a personal_samples
  REC_PORT              default 8789
"@
}

if ($Help) {
    Show-Help
    exit 0
}

if ($Blackwell -and $Cpu) {
    throw "-Blackwell requiere GPU NVIDIA. No combines con -Cpu (RX 6750 XT / AMD)."
}

$gpuKind = Get-TrainerGpuKind
$useGpu = -not $Cpu
if ($Cpu) {
    $useGpu = $false
} elseif ($gpuKind -ne "nvidia") {
    Write-Log "GPU detectada: $gpuKind — CUDA no aplica (AMD Radeon RX 6750 XT o desconocida)."
    Write-Log "Forzando modo CPU (omite --gpus all). Pasa -Cpu para silenciar este aviso."
    $useGpu = $false
}

if ($Blackwell -and -not $useGpu) {
    throw "-Blackwell requiere GPU NVIDIA. Este equipo parece AMD/CPU."
}

Write-Log "Wake word=$WakeWord image=$Image gpu_kind=$gpuKind use_gpu=$useGpu"
Write-Log "DATA_DIR=$DataDir (personal_samples -> $DataDir\personal_samples)"

if (-not $DryRun) {
    if (-not (Test-Command "wsl")) {
        Write-Log "WSL no encontrado. Instala con: wsl --install   (Ubuntu) y reinicia."
    } else {
        Write-Log "WSL detectado"
    }
    if (-not (Test-Command "docker")) {
        throw "Docker no esta en PATH. Instala Docker Desktop (backend WSL2) y reinicia la sesion."
    }
    if ($useGpu) {
        if (Test-Command "nvidia-smi") {
            Write-Log "nvidia-smi OK — el contenedor usara --gpus all"
        } else {
            Write-Log "AVISO: nvidia-smi no esta en PATH. El contenedor puede caer a CPU."
        }
    } else {
        Write-Log "Modo CPU: docker run sin --gpus all"
    }
}

$personalDest = Join-Path $DataDir "personal_samples"
New-Item -ItemType Directory -Force -Path $personalDest, (Join-Path $DataDir "trained_wake_words") | Out-Null

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
    Write-Log "Copiados $copied WAV a personal_samples desde $src"
    break
}
if ($copied -eq 0) {
    Write-Log "No hay WAV en personal_samples del repo. Transfiere la carpeta exportada desde el Mac."
}

$dockerRunParts = @(
    "docker run -d",
    "--name $ContainerName"
)
if ($useGpu) {
    $dockerRunParts += "--gpus all"
}
$dockerRunParts += @(
    "-p ${RecPort}:${RecPort}",
    "-e REC_PORT=$RecPort",
    "-v `"${DataDir}:/data`"",
    $Image
)
$dockerRun = $dockerRunParts -join " "

if ($DryRun) {
    Write-Log "dry-run: docker pull $Image"
    Write-Log "dry-run: $dockerRun"
} else {
    Write-Log "docker pull $Image"
    docker pull $Image
    $existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
    if ($existing) {
        Write-Log "Contenedor $ContainerName ya existe — docker start"
        Write-Log "Si se creo con --gpus all en un PC AMD, borralo: docker rm -f $ContainerName"
        docker start $ContainerName | Out-Null
    } else {
        $runArgs = @("run", "-d", "--name", $ContainerName)
        if ($useGpu) { $runArgs += @("--gpus", "all") }
        $runArgs += @("-p", "${RecPort}:${RecPort}", "-e", "REC_PORT=$RecPort", "-v", "${DataDir}:/data", $Image)
        docker @runArgs
    }
}

Write-Log "UI: http://127.0.0.1:$RecPort"
Write-Log "Trainer -> wake word=mariano, language=Spanish, Start training"
$next = ".\train_mariano_windows.ps1"
if (-not $useGpu) { $next = ".\train_mariano_windows.ps1 -Cpu" }
Write-Log "Siguiente: $next"
if ($Blackwell) {
    Write-Log "Blackwell: usa esta imagen solo en RTX 50-series"
}
if (-not $useGpu) {
    Write-Log "CPU: el train sera mas lento; 16 GB RAM es justo — cierra el resto de apps."
}
