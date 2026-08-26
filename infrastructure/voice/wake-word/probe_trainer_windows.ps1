#requires -Version 5.1
<#
.SYNOPSIS
  Diagnostica si este Windows 11 puede entrenar microWakeWord y cómo.

.DESCRIPTION
  El PC WayneHomeLab de entrenamiento es AMD (Ryzen 5 3600 + Radeon RX 6750 XT).
  CUDA (--gpus all) no aplica. Este script dice si hay que usar -Cpu, cuánta RAM
  y disco hay, y si Docker/WSL2 están listos.

.PARAMETER Help
  Muestra la ayuda.
#>
[CmdletBinding()]
param(
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    Write-Host "[probe-trainer-windows] $Message"
}

if ($Help) {
    @"
Uso: .\probe_trainer_windows.ps1 [-Help]

Inspecciona GPU (NVIDIA vs AMD Radeon), RAM, disco, WSL y Docker.
En el PC con RX 6750 XT el resultado esperado es modo CPU (sin --gpus all).
"@
    exit 0
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
        $gpus = @(Get-CimInstance Win32_VideoController -ErrorAction Stop)
        foreach ($g in $gpus) {
            $name = [string]$g.Name
            if ($name -match "NVIDIA") { return "nvidia" }
            if ($name -match "AMD|Radeon") { return "amd" }
        }
    } catch {
        Write-Log "No se pudo enumerar GPUs: $($_.Exception.Message)"
    }
    return "unknown"
}

function Get-GpuNames {
    $names = @()
    try {
        foreach ($g in @(Get-CimInstance Win32_VideoController -ErrorAction Stop)) {
            if ($g.Name) { $names += [string]$g.Name }
        }
    } catch {
        $names += "(no enumeradas)"
    }
    if ($names.Count -eq 0) { return "(ninguna)" }
    return ($names -join ", ")
}

$gpuKind = Get-TrainerGpuKind
$gpuNames = Get-GpuNames
$ramBytes = [int64](Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
$ramGiB = [math]::Round($ramBytes / 1GB, 1)
$dataDir = if ($env:MWW_NVIDIA_DATA_DIR) { $env:MWW_NVIDIA_DATA_DIR } else { Join-Path $HOME "mww-data" }
$drive = Get-Item $HOME
$disk = Get-PSDrive -Name $drive.PSDrive.Name
$freeGiB = [math]::Round($disk.Free / 1GB, 1)

Write-Log "GPU: $gpuNames"
Write-Log "gpu_kind=$gpuKind"
Write-Log "RAM: ${ramGiB} GiB"
Write-Log "Disco libre ($($drive.PSDrive.Name):): ${freeGiB} GiB"
Write-Log "DATA_DIR=$dataDir"

if (Test-Command "wsl") {
    Write-Log "WSL: presente"
} else {
    Write-Log "WSL: AUSENTE — instala con: wsl --install"
}

if (Test-Command "docker") {
    Write-Log "Docker: presente"
} else {
    Write-Log "Docker: AUSENTE — instala Docker Desktop (backend WSL2)"
}

if ($gpuKind -eq "nvidia") {
    Write-Log "Recomendacion: GPU NVIDIA -> .\setup_trainer_windows.ps1"
    Write-Log "CUDA / --gpus all aplica en este equipo."
} else {
    Write-Log "Recomendacion: modo CPU -> .\setup_trainer_windows.ps1 -Cpu"
    Write-Log "CUDA no aplica (AMD Radeon RX 6750 XT / sin NVIDIA)."
    Write-Log "ROCm oficial no cubre RX 6750 XT (gfx1031). DirectML no esta en la imagen Tater."
}

if ($ramGiB -lt 24) {
    Write-Log "AVISO: ${ramGiB} GiB RAM es justo. Cierra Chrome/juegos. En %UserProfile%\.wslconfig usa memory=10GB."
}

if ($freeGiB -lt 80) {
    Write-Log "AVISO: ${freeGiB} GiB libres. El primer train pide ~80 GB (TTS + negativos)."
}

Write-Log "Siguiente: copia personal_samples\*.wav al clone y ejecuta setup_trainer_windows.ps1 -Cpu"
