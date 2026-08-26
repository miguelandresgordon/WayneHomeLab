#!/usr/bin/env python3
"""Local microphone recorder for speaker-id enrollment (runs on the Mac).

Records short 16 kHz mono WAV clips directly from the Mac microphone and
organizes them under ``samples/<speaker>/``. Files are tiny (~128 KB / 4 s),
so the whole enrollment set fits in a few MB — easy to sync to Google Drive.

Why local (not Colab)?
  - The Colab kernel runs remotely: it has no access to your Mac microphone.
  - Browser JS recording only works in the Colab web UI, not Cursor's renderer.
  - Recording locally gives clean 16 kHz mono WAV with no transcoding.

Workflow:
  1. python3 record_samples.py --speaker miguel --count 10
  2. Repeat for each person.
  3. Copy the resulting ``samples/`` folder to Google Drive
     (MyDrive/wayne-speaker-id/samples/) and run the Colab notebook.

Dependencies (Mac):
  brew install portaudio
  pip3 install sounddevice soundfile numpy

Alternative without sounddevice (ffmpeg avfoundation):
  ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -t 4 samples/miguel/clip01.wav
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SAMPLE_RATE = 16000
DEFAULT_DURATION = 4.0
DEFAULT_COUNT = 10

SUGGESTED_PHRASES = [
    "Mariano, enciende la luz del salón",
    "¿Qué tiempo hace hoy?",
    "Pon música tranquila por favor",
    "Sube el volumen de la televisión",
    "Apaga todas las luces de la casa",
    "Mariano, ¿qué hora es?",
    "Recuérdame comprar pan mañana",
    "Baja la temperatura un par de grados",
    "Enciende la lámpara del dormitorio",
    "¿Tengo alguna notificación nueva?",
    "Pon el temporizador a diez minutos",
    "Mariano, buenas noches",
]


def _require_audio_libs():
    try:
        import numpy as np  # noqa: F401
        import sounddevice as sd
        import soundfile as sf  # noqa: F401
    except ImportError as exc:
        print("ERROR: faltan dependencias de audio.", file=sys.stderr)
        print("Instala con:", file=sys.stderr)
        print("  brew install portaudio", file=sys.stderr)
        print("  pip3 install sounddevice soundfile numpy", file=sys.stderr)
        print(f"(detalle: {exc})", file=sys.stderr)
        sys.exit(1)
    return sd


def record_clip(out_path: Path, duration: float, sample_rate: int) -> None:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    frames = int(duration * sample_rate)
    recording = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    audio = np.ascontiguousarray(recording[:, 0])

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, audio, sample_rate, subtype="PCM_16")

    if peak < 0.01:
        print(f"  AVISO: nivel muy bajo (peak={peak:.4f}). ¿Micrófono silenciado?")


def existing_clip_count(speaker_dir: Path) -> int:
    if not speaker_dir.is_dir():
        return 0
    return len(list(speaker_dir.glob("*.wav")))


def run(
    speaker: str,
    count: int,
    duration: float,
    output_dir: Path,
    sample_rate: int,
    countdown: int,
) -> None:
    sd = _require_audio_libs()

    try:
        default_input = sd.query_devices(kind="input")
        print(f"Micrófono: {default_input['name']}")
    except Exception as exc:  # pragma: no cover - device dependent
        print(f"AVISO: no se pudo consultar el micrófono ({exc})")

    speaker_dir = output_dir / speaker
    start_index = existing_clip_count(speaker_dir)
    print(f"\nPersona: {speaker}")
    print(f"Clips existentes: {start_index} | objetivo nuevo: {count}")
    print(f"Duración por clip: {duration}s @ {sample_rate} Hz mono")
    print("Consejo: varía frases, distancia y tono. Incluye algo de ruido real.\n")

    recorded = 0
    for i in range(count):
        clip_number = start_index + i + 1
        phrase = SUGGESTED_PHRASES[(clip_number - 1) % len(SUGGESTED_PHRASES)]
        filename = f"clip_{clip_number:02d}.wav"
        out_path = speaker_dir / filename

        print(f"[{i + 1}/{count}] Frase sugerida: «{phrase}»")
        try:
            input("    Pulsa Enter para grabar (Ctrl+C para salir)... ")
        except (KeyboardInterrupt, EOFError):
            print("\nGrabación interrumpida.")
            break

        for remaining in range(countdown, 0, -1):
            print(f"    Grabando en {remaining}...", end="\r", flush=True)
            time.sleep(1)

        print("    ● Grabando ahora — habla...        ")
        record_clip(out_path, duration, sample_rate)
        recorded += 1
        print(f"    Guardado: {out_path}\n")

    total = existing_clip_count(speaker_dir)
    print(f"Listo. {recorded} clip(s) nuevos. Total para '{speaker}': {total}")
    print(f"Carpeta: {speaker_dir.resolve()}")
    if total < 8:
        print("AVISO: se recomiendan 8+ clips por persona para un perfil robusto.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--speaker", required=True, help="Nombre (minúsculas, sin espacios)")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Clips a grabar")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Segundos por clip")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "samples",
        help="Carpeta base de muestras (default: ./samples)",
    )
    parser.add_argument("--samplerate", type=int, default=SAMPLE_RATE, help="Frecuencia de muestreo")
    parser.add_argument("--countdown", type=int, default=2, help="Cuenta atrás antes de grabar")
    args = parser.parse_args()

    speaker = args.speaker.strip().lower()
    if not speaker or " " in speaker:
        print("ERROR: --speaker debe ser una sola palabra en minúsculas", file=sys.stderr)
        return 1

    run(
        speaker=speaker,
        count=args.count,
        duration=args.duration,
        output_dir=args.output_dir,
        sample_rate=args.samplerate,
        countdown=args.countdown,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
