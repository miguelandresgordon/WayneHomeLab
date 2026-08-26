# Entrenar «Mariano» desde el móvil (sin Mac)

Guía para arrancar el **primer train** en RunPod **solo con Safari / Cursor iOS**. No hace falta `runpodctl` ni el Mac hasta **después** de que existan `mariano.tflite` + `mariano.json`.

Guía completa (PC + teardown): [runpod-train-mariano.md](runpod-train-mariano.md).  
Runbook Satellite1: [wake-word-mariano.md](wake-word-mariano.md).

Los **34 WAV** de Assist **no están en git** (gitignored). Desde el iPhone no puedes subirlos con runpodctl. Abajo hay tres formas de cubrir las muestras.

---

## Qué puedes hacer ahora (iPhone)

1. Revisar billing (Auto-pay OFF, alerta $10).
2. Crear network volume **200 GB**.
3. Desplegar **1× GPU Pod on-demand** (imagen Tater, volume en `/data`, HTTP 8789).
4. Subir o grabar muestras en la UI.
5. Lanzar `train` y dejarlo corriendo en el pod (puedes bloquear el teléfono).

## Qué no puedes hacer hasta el Mac

- Copiar el modelo al repo (`copy_model_from_trainer.sh`).
- Flashear Satellite1.
- Borrar el volume con `teardown_runpod_trainer.sh` (sí puedes **Stop/Terminate** en la consola; el volume hay que borrarlo a mano o más tarde).

**No dejes el pod Running** cuando el train haya acabado. Con $50 y una RTX 4090 Secure (~$0.69/h) el techo de ~48 h sigue cubierto, pero cada hora extra come crédito.

---

## Antes de tocar Deploy — 60 segundos

| Hacer | No hacer |
|-------|----------|
| [Pods](https://www.console.runpod.io/pods) → **Deploy** / **+ New → Pod** | **Instant Cluster** (multi-nodo, para LLM) |
| On-demand | **Spot** (lo pueden matar con 5 s de aviso) |
| **1 GPU** | 2+ GPUs |
| Imagen `ghcr.io/tatertotterson/microwakeword:latest` | Templates PyTorch / Jupyter por defecto |
| Volume montado en **`/data`** | Dejar el mount en `/workspace` |
| HTTP **8789** | Confiar solo en Jupyter 8888 (la imagen Tater no trae `/start.sh` de RunPod) |

Con **$50** ya recargados: gasto esperado del train **~$8–20** de GPU + **~$0.47/día** del volume **200 GB**. El riesgo no es el train: es **olvidarse el pod encendido**.

Network volumes de RunPod van con **Secure Cloud** (mismo datacenter que el volume). Community es más barato (~$0.34/h) pero **sin** network volume: si terminas el pod, pierdes `/data`. Desde el móvil, usa **Secure + network volume**. $50 cubren ~48 h de 4090 Secure.

---

## Paso 0 — Billing (1 min)

Abre [Billing](https://www.console.runpod.io/user/billing) en Safari (si la UI se ve rara: **Aa → Request Desktop Website**).

1. Confirma saldo **~$50**.
2. **Auto-pay: OFF** (si está ON, apágalo).
3. **Low balance alert** → umbral **$10** (email; no para el pod).
4. Anota un recordatorio en el iPhone a **+12 h**, **+24 h** y **+48 h**: «¿sigue Running el pod Mariano?».

La consola **no** siempre muestra `--stop-after 48h` (eso es CLI). El kill switch real desde el móvil es: recordatorios + Stop/Terminate a mano. Opcional: watchdog en el propio pod (paso 5).

---

## Paso 1 — Network volume (persistencia)

El volume sobrevive si el pod se para, se termina o se acaba el saldo. **Créalo antes** del pod: no se puede enganchar después.

1. [Storage](https://www.console.runpod.io/user/storage) → **New Network Volume**.
2. Nombre: `waynelab-mww-data`.
3. Tamaño: **200 GB** (se puede subir después, no bajar). 100 GB **no basta**: AudioSet sin cleanup llena la cuota y el trainer muere con Exit 999.
4. Tier: **Standard** (~$0.07/GB/mes). No hace falta High-Performance.
5. Datacenter: elige uno con RTX 4090 Secure (EU si hay stock, p. ej. el que muestre 4090). **Anota el datacenter y el Volume ID.**
6. **Create Network Volume**.

---

## Paso 2 — Desplegar el GPU Pod

[Pods](https://www.console.runpod.io/pods) → **+ New → Pod** (o **Deploy**).

La consola tiene dos flujos (Early Access vs legado). Los **valores** son los mismos.

### 2.1 Filtro de volume (importante)

En Compute / filtros, selecciona el network volume `waynelab-mww-data`. La lista de GPU se reduce al **mismo datacenter**. Si no filtras, puedes desplegar una 4090 en otro DC y el volume **no monta**.

Si el volume se puede adjuntar en **Community**, elige Community (más barato, ~$0.34/h). Si la consola solo deja **Secure Cloud** con network volume, usa Secure (~$0.69/h); $50 siguen cubriendo ~48 h.

### 2.2 GPU

| Preferencia | GPU | Notas |
|-------------|-----|--------|
| 1ª | **1× RTX 4090** | Community si el volume se adjunta; si no, Secure |
| 2ª | RTX 3090 / A5000 / A4000 | Más barata, suficiente |
| Evitar | H100 / A100 / Instant Cluster | Overkill |

**On-Demand**, **1 GPU**, nunca Spot. Mira el **$/h** en el Summary antes de confirmar.

Si pone **Out of capacity**: **Deploy when available** (email ON, ventana 24 h) **o** baja a 3090/A4000 en el **mismo** datacenter del volume. No dejes una suscripción olvidada si también vas a desplegar otra GPU a mano.

### 2.3 Template / imagen

No uses un template PyTorch.

1. Template → **Edit** / **Change** / **Set overrides**.
2. Container image:

   ```text
   ghcr.io/tatertotterson/microwakeword:latest
   ```

3. Container disk: **50 GB**.
4. Persistent storage: el network volume del paso 1.
5. **Volume mount path: `/data`** (contrato Tater; si queda `/workspace` el train escribe en disco efímero).
6. Expose HTTP: **8789** (`8789/http`). TCP 22 opcional.
7. **Start Jupyter: OFF** (la UI del trainer es 8789; Jupyter suele fallar en esta imagen).
8. Pod name: `waynelab-mww-mariano`.

### 2.4 Deploy

1. Revisa Summary: 1× GPU, imagen Tater, volume, **$/h**.
2. **Deploy Pod** / **Deploy On-Demand**.
3. Espera **Running** (el pull de la imagen puede tardar varios minutos).
4. Anota el **Pod ID**.

Si el pod entra en Error: Edit no arregla un mount mal puesto. **Terminate** (el volume no se borra) y vuelve a Deploy con `/data`.

---

## Paso 3 — Comprobar GPU y disco

Pod → **Connect** → **Web Terminal** (no hace falta SSH).

```bash
nvidia-smi
df -h /data
ls -la /data
mkdir -p /data/personal_samples /data/trained_wake_words
```

Esperado: una NVIDIA en `nvidia-smi`, `/data` con ~200 GB de cuota. Si `nvidia-smi` falla, no entrenes: eliges mal la GPU o la imagen.

**Justo después**, instala el wrapper de `tar` (permisos uid 1020 en Network Volume):

```bash
cat > /usr/local/bin/tar << 'EOF'
#!/bin/sh
exec /usr/bin/tar --no-same-owner --no-same-permissions "$@"
EOF
chmod +x /usr/local/bin/tar
```

---

## Paso 4 — Muestras (elige una y no mezcles a medias)

Las muestras personales **mejoran** que el modelo te reconozca a ti; no son obligatorias. Si las añades **después** de un train TTS-only, hay que **re-entrenar** (otra pasada de GPU).

### Opción A — Los 34 WAV de Assist (mejor)

Si los tienes en **Archivos / iCloud / WhatsApp / mail**:

1. Pod → **Connect** → enlace **HTTP :8789** (UI Tater).
2. Pestaña **Samples**.
3. Upload en **Personal** (acepta WAV, M4A, MP3, …; convierte a 16 kHz mono).
4. Cuenta ~34 clips. No pulses Clear.

### Opción B — Grabar «Mariano» ahora en el iPhone (buena)

Mejor que TTS-only. No sustituye del todo a los 34 del Satellite1 (mic distinto), pero vale para **empezar hoy**.

1. App **Notas de voz**: 20–30 tomas, una palabra: «Mariano».
2. Varía distancia, volumen y un poco de ruido de casa. Evita la TV alta.
3. Comparte cada toma (o un álbum) → **Archivos**.
4. En la UI Tater → **Samples → Personal → Upload** (M4A vale).

### Opción C — TTS-only (aceptable para no bloquear)

En **Trainer**, si pide confirmación con 0 personal samples, confirma. El modelo saldrá de voces sintéticas en español. Más falsos negativos con tu voz; se puede re-entrenar cuando tengas los 34 WAV.

---

## Paso 5 — Lanzar el train

### Recomendado desde el móvil — UI

1. **Connect → HTTP :8789**.
2. Pestaña **Trainer**.
3. Wake word: **mariano** (minúsculas).
4. Language: **Spanish**.
5. TTS: deja el default (ensemble). No hace falta Auto Training.
6. Confirma recuento de personal samples (o 0 + confirmación).
7. **Start training**.
8. Espera a ver logs en el popup (descarga TTS, features, fit). Cuando **sigan saliendo líneas**, ya corre **en el pod**.

Puedes bloquear el iPhone y cerrar Safari. El train **no** depende de que el móvil esté despierto.

### Reserva — CLI en tmux (si 8789 no abre)

Web Terminal:

```bash
tmux new -s mariano
command -v train_wake_word && train_wake_word --language=Spanish mariano
# Si no existe train_wake_word, usa la UI HTTP 8789; no improvises otro entrypoint.
```

Desacoplar: `Ctrl+B`, suelta, `D`. Volver: `tmux attach -t mariano`.  
En teclado iPhone eso es incómodo: prioriza la UI.

### Kill switch dentro del pod (opcional)

Otra sesión de Web Terminal (el volume **sí** sobrevive a un terminate):

```bash
# Para el cobro de GPU a las 48 h. El network volume NO se borra.
# Comprueba que RUNPOD_POD_ID no está vacío antes.
echo "POD=$RUNPOD_POD_ID"
command -v runpodctl && nohup sh -c 'sleep 48h; runpodctl remove pod "$RUNPOD_POD_ID"' >/tmp/mww-killswitch.log 2>&1 &
```

Si `runpodctl` no está en la imagen Tater, ignora este bloque y usa los recordatorios del iPhone. **Nunca** `remove` si desplegaste **sin** network volume (perderías el modelo).

---

## Paso 6 — Cómo saber que acabó (sin el Mac)

Cada 6–12 h, Safari → Pods:

1. El pod sigue **Running** (si está Exited/Stopped a $0, recarga y monta el **mismo** volume en un pod nuevo).
2. **HTTP :8789** → pestaña **Wake Words**: debe aparecer **mariano**.
3. Web Terminal:

   ```bash
   ls -lh /data/trained_wake_words/mariano.tflite /data/trained_wake_words/mariano.json
   ls -ld /data/output/*mariano* 2>/dev/null | tail
   ```

Artefactos que importan:

```text
/data/trained_wake_words/mariano.tflite
/data/trained_wake_words/mariano.json
```

(La imagen también escribe copias bajo `/data/output/<timestamp>-mariano-…/`.)

Duración realista: **4–24 h** (la 1ª pasada se va sobre todo en TTS/features, no en el fit). Si a las 36 h no hay `.tflite`, mira el popup de logs o `tmux attach`; no lances un segundo train en paralelo.

---

## Paso 7 — Cuando existan los dos ficheros

**Orden fijo:**

1. **No borres el volume.**
2. Si no tienes Mac ahora: **deja el pod Stopped/Terminated** (con network volume los ficheros siguen en `waynelab-mww-data`) **o** déjalo Running solo si vas a descargar en minutos. Con NV, Terminate del pod **no** borra el volume; Stop a veces **no está disponible** con NV (solo Terminate).
3. En el Mac, más tarde:
   - Pod nuevo **barato** (incluso CPU) con el **mismo** volume en `/data`, **o** el GPU pod si aún está.
   - `runpodctl receive` / `teardown_runpod_trainer.sh` (ver [runpod-train-mariano.md](runpod-train-mariano.md)).
   - `MWW_RUNPOD_DATA_DIR=$HOME/mww-runpod ./infrastructure/voice/wake-word/copy_model_from_trainer.sh`.
4. Cuando `mariano.{tflite,json}` estén en el repo: borra el volume en Storage (si no, **~$0.23/día** para siempre).

Descargar el `.tflite` por mail/iCloud desde el Web Terminal es posible (`python3 -m http.server` no expone bien sin puerto). **No improvises HTTP abierto.** Espera al Mac.

---

## Si el saldo llega a $0 a mitad

Con network volume:

- RunPod **para** el pod; **`/data` se conserva**.
- Recargas, **Deploy de otro pod** con el **mismo** volume en `/data`, mismo datacenter.
- Reanudas o relanzas el train (si el job se cortó a mitad, suele hacer falta relanzar; TTS/features ya descargados en `/data` se reutilizan).

Sin volume, un pod terminado **pierde** el disco.

---

## Fallos típicos desde el móvil

| Síntoma | Qué hacer |
|---------|-----------|
| HTTP 8789 no abre | Espera 2–3 min al pull; Connect otra vez. Web Terminal: `ps aux` y `df -h /data`. Confirma puerto **8789/http**. |
| Jupyter 8888 error | Normal. Usa 8789 + Web Terminal. |
| `nvidia-smi` vacío | GPU mal / imagen CPU. Terminate y redespliega 4090/3090. |
| Pod Running pero `/data` vacío o 20 GB | Mount no es el NV o path `/workspace`. Redesplegar con `/data`. |
| Instant Cluster / varias GPU | Cancela. Un solo GPU Pod. |
| Community + NV incompatible | Esperado. Secure Cloud + el volume del paso 1. |
| Safari se duerme | Irrelevante si el train ya escribió logs. El job está en el pod. |

---

## Checklist (esta sesión)

```
[ ] Auto-pay OFF · ~$50 · alerta $10 · recordatorios 12/24/48 h
[ ] Volume **200 GB** Standard · mismo DC que la GPU · ID anotado
[ ] Wrapper `tar --no-same-owner` en `/usr/local/bin/tar` tras Start
[ ] Pod on-demand Secure · 1× 4090 (o 3090/A4000) · imagen Tater
[ ] Container 50 GB · NV en /data · HTTP 8789 · Jupyter OFF · no Spot
[ ] nvidia-smi OK · df /data ~100G
[ ] Samples: 34 WAV  o  20–30 M4A  o  TTS-only confirmado
[ ] Trainer: mariano / Spanish / Start  (logs en marcha)
[ ] Teléfono se puede bloquear
[ ] NO Terminate el volume · NO segundo train paralelo
[ ] Cuando existan mariano.tflite+json: para el pod; descarga en el Mac
```

---

## Referencias

- Consola: [Pods](https://www.console.runpod.io/pods) · [Storage](https://www.console.runpod.io/user/storage) · [Billing](https://www.console.runpod.io/user/billing)
- [RunPod billing](https://docs.runpod.io/accounts-billing/billing) · [Network volumes](https://docs.runpod.io/storage/network-volumes)
- [Imagen Tater NVIDIA Docker](https://github.com/TaterTotterson/microWakeWord-Trainer-Nvidia-Docker)
