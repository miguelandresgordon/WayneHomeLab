# Guion de enrolado — Speaker ID (alicia, miguel)

Cada persona, a solas en el salón y a su distancia habitual del Satellite1
(2–3 m), dice estas 12 órdenes **reales** (las que usáis a diario). Antes de
cada una: «Mariano», espera el pitido, di la frase, espera la respuesta.

Sesión de **alicia** y sesión de **miguel** por separado (no mezcléis voces en
la misma sesión). Con la radio y la tele apagadas; una segunda sesión con la
tele baja hace el perfil más robusto.

1. Pon la SER.
2. Para la radio.
3. Enciende la lámpara.
4. Pon la lámpara al 50 por ciento.
5. Apaga la lámpara.
6. Enciende la tele.
7. Apaga la tele.
8. Pon Radio 3.
9. Sube el volumen.
10. Baja el volumen.
11. Pon música de Rosalía.
12. Siguiente canción.

## Pasos

```bash
date +%Y-%m-%dT%H:%M          # apunta la hora ANTES de empezar, p. ej. 2026-11-27T10:00
# ... di las 12 frases al Satellite1 ...
./infrastructure/voice/speaker-id/enroll_speaker.sh alicia 2026-11-27T10:00
```

Repite con `miguel` (tu perfil actual es de junio y con el micro del Mac).
Alternativa sin Satellite1: `record_samples.py --speaker alicia` (micro del Mac;
peor parecido con el audio real).
