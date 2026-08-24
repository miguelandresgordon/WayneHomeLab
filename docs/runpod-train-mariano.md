# Guía de inicio — Entrenar «Mariano» en RunPod

Guía paso a paso para el **primer entrenamiento** de la wake word «Mariano» en un **GPU Pod on-demand** (1× NVIDIA). Es un trabajo **puntual**: enciendes la GPU, entrenas, descargas el modelo y apagas.

**¿Estás en el iPhone / sin Mac?** No uses esta guía (asume `runpodctl` en un PC). Sigue [runpod-train-mariano-movil.md](runpod-train-mariano-movil.md).

Runbook completo (captura de muestras, flash Satellite1, afinado): [wake-word-mariano.md](wake-word-mariano.md).

Scripts del repo: `infrastructure/voice/wake-word/`.

---

## ¿Es un gasto puntual o recurrente?

Son **dos cosas distintas** en la factura de RunPod:

| Recurso | Qué es | Cuándo cobra | ¿Puntual? |
|---------|--------|--------------|-----------|
| **GPU Pod** | Máquina con GPU para entrenar | Por segundo **mientras el pod está Running** | **Sí** — paras el pod → deja de cobrar GPU |
| **Network volume** | Disco en red persistente (TTS, features, WAV, modelo) | Por GB almacenado **mientras el volume exista**, aunque el pod esté parado | **No** — sigue cobrando hasta que **borres** el volume |

El **entrenamiento es puntual**. El gasto «recurrente» del que se habla en el runbook **no es el train**: es el alquiler del **network volume** si lo dejas creado después de terminar.

RunPod cobra el volume a **~$0.07/GB/mes** (&lt;1 TB). Con 100 GB ≈ **$7/mes** ≈ **$0.23/día** mientras no lo elimines. No depende de que haya un pod encendido.

**Cómo cerrar el ciclo sin sorpresas:**

1. Descarga `mariano.{tflite,json}` a tu PC.
2. **Stop** el pod (corta el coste de GPU).
3. **Delete** el network volume (corta el coste de almacenamiento).

Si borras el volume, pierdes los datos intermedios del train (TTS, features). Para un único entrenamiento no importa: lo que necesitas conservar son los dos ficheros del modelo en tu repo.

**Alternativa:** mantener el volume unos días por si quieres re-entrenar sin regenerar TTS; entonces sí pagas esos ~$0.23/día a cambio de comodidad.

---

## ¿Cuánto dinero recargar?

RunPod **no** tiene tope «no gastes más de X€». El límite real es la **cartera prepago** con **Auto-pay OFF**.

| Recarga | Para qué sirve |
|---------|----------------|
| **$15–25** | Suficiente si paras el pod al terminar y borras el volume (~$5–15 de GPU en un primer run) |
| **$50–55** | Techo cómodo si quieres margen sin recargar a mitad de noche |
| **$5 actuales** | No fiable: RunPod pide saldo para ≥1 h de la GPU elegida y puede **parar el pod** si se agota |

**Gasto real esperado del train** (RTX 4090 Community ~$0.34/h; confirma en consola al Deploy):

- 8 h ≈ $3 · 24 h ≈ $8 · 48 h ≈ $16  
- Volume durante el train (1–2 días): despreciable frente a la GPU  
- Volume **olvidado** 30 días: ~$7 extra

Los créditos **no se reembolsan**. Deposita lo que estés dispuesto a perder como máximo.

---

## Requisitos previos

- Cuenta [RunPod](https://www.console.runpod.io) con saldo (recomendado **$20–25** mínimo).
- Muestras personales en `infrastructure/voice/wake-word/personal_samples/*.wav` (gitignored; ~34 WAV exportados con `export_personal_samples.sh`).
- Scripts `.sh`: en **macOS Tahoe** usa zsh (`zsh ./teardown_runpod_trainer.sh` o `./…` con shebang bash). En Windows: Git Bash o WSL.
- Opcional: [runpodctl](https://docs.runpod.io/runpodctl/overview) para subir/bajar archivos.

**No uses:** Instant Cluster (multi-nodo, para LLM) ni **Spot** (preemptible; puede cortar el job con 5 s de aviso).

---

## Paso 0 — Revisar el checklist local

```bash
cd infrastructure/voice/wake-word
# macOS (zsh): también vale  zsh ./setup_trainer_runpod.sh --dry-run
./setup_trainer_runpod.sh --dry-run
./train_mariano_runpod.sh --dry-run
```

El primer script imprime imagen Docker, GPU, puertos, `--stop-after` y un ejemplo de `runpodctl pod create`. **No crea nada en RunPod.**

---

## Paso 1 — Billing

1. [Billing](https://www.console.runpod.io/user/billing)
2. **Auto-pay: OFF**
3. Recarga **$20–25** (o $50 si quieres techo amplio)
4. **Low balance alert** → umbral **$10** (solo email)

Documentación: [RunPod billing](https://docs.runpod.io/accounts-billing/billing).

---

## Paso 2 — Network volume (persistencia del train)

1. [Storage → Network Volumes](https://www.console.runpod.io/user/storage) → **Create**
2. Nombre: `waynelab-mww-data`
3. Tamaño: **100 GB** (primera pasada TTS + features puede usar 25–80 GB)
4. Datacenter: el mismo donde desplegarás la GPU (p. ej. región EU si hay RTX 4090)
5. Anota el **Volume ID**

Montaje obligatorio en **`/data`** (contrato de la imagen Tater). No uses solo `/workspace`.

---

## Paso 3 — Desplegar GPU Pod

En [Pods → Deploy](https://www.console.runpod.io/pods):

| Campo | Valor |
|-------|--------|
| Pricing | **On-demand** (nunca Spot) |
| Cloud | **Community** |
| GPU | **1× RTX 4090** (alternativa barata: RTX A4000 ~$0.17/h) |
| Container image | `ghcr.io/tatertotterson/microwakeword:latest` |
| Container disk | 50 GB |
| Network volume | el de paso 2 → mount **`/data`** |
| HTTP port | **8789** |
| Auto-stop | **48 h** (`--stop-after 48h`) |

Verifica el **$/h** en pantalla antes de confirmar.

Equivalente CLI (sustituye `VOLUME_ID`):

```bash
runpodctl pod create \
  --name waynelab-mww-mariano \
  --gpu-type "NVIDIA GeForce RTX 4090" \
  --image ghcr.io/tatertotterson/microwakeword:latest \
  --container-disk 50 \
  --volume-mount-path /data \
  --network-volume-id VOLUME_ID \
  --ports 8789/http,22/tcp \
  --stop-after 48h \
  --cloud COMMUNITY
```

Cuando esté **Running**, anota el **Pod ID**.

---

## Paso 4 — Subir muestras personales

En local:

```bash
cd infrastructure/voice/wake-word
./train_mariano_runpod.sh
# Sustituye POD_ID
runpodctl send personal_samples POD_ID
```

En el pod (Web Terminal):

```bash
ls /data/personal_samples/*.wav | wc -l
# Esperado: ~34
```

---

## Paso 5 — Entrenar

### Comprobar GPU

```bash
nvidia-smi
```

### Opción A — CLI en tmux (recomendada)

Sobrevive al cierre del navegador:

```bash
tmux new -s mariano
train_wake_word --language=Spanish mariano
```

Desacoplar: `Ctrl+B`, `D`. Volver: `tmux attach -t mariano`.

### Opción B — UI web

Pod → **Connect** → enlace **HTTP :8789** → Trainer → wake word **mariano** → language **Spanish** → confirma `personal_samples` → **Start training**.

La primera ejecución tarda más (descarga TTS, genera negativos). Estimación: **4–24 h** según GPU y carga.

Artefactos finales:

```text
/data/trained_wake_words/mariano.tflite
/data/trained_wake_words/mariano.json
```

---

## Paso 6 — Descargar, apagar y no dejar nada cobrando

Orden **fijo**: primero el modelo en tu PC, luego **Stop** del pod, luego (opt-in) borrar el volume. Si paras o borras antes de descargar, puedes perder el train.

### Automatizado (`teardown_runpod_trainer.sh`)

El script vive en **tu PC**. No borra el volume por defecto.

```bash
cd infrastructure/voice/wake-word

# 1) En el pod, cuando existan los ficheros, envíalos:
#    runpodctl send /data/trained_wake_words/mariano.tflite \
#                  /data/trained_wake_words/mariano.json
# 2) En el PC: runpodctl receive  →  mueve a ~/mww-runpod/trained_wake_words/

MWW_RUNPOD_POD_ID=POD_ID \
  ./teardown_runpod_trainer.sh --dry-run

# Cuando mariano.{tflite,json} estén en ~/mww-runpod/trained_wake_words/:
MWW_RUNPOD_POD_ID=POD_ID \
  ./teardown_runpod_trainer.sh

# Corta también el alquiler del disco (destructivo; solo tras verificar el modelo):
MWW_RUNPOD_POD_ID=POD_ID \
MWW_RUNPOD_VOLUME_ID=VOLUME_ID \
  ./teardown_runpod_trainer.sh --delete-volume

# Esperar a que aparezcan artefactos (SSH o ficheros locales), intervalo 60s:
# MWW_RUNPOD_SSH='ssh root@… -p …' ./teardown_runpod_trainer.sh --watch
```

Sin `--delete-volume` el **volume sigue cobrando** (~$0.23/día) aunque el pod esté parado.

Luego copia al repo:

```bash
MWW_RUNPOD_DATA_DIR="$HOME/mww-runpod" \
  ./infrastructure/voice/wake-word/copy_model_from_trainer.sh
# macOS: zsh ./infrastructure/voice/wake-word/copy_model_from_trainer.sh
```

Siguiente paso del proyecto: servir modelo y flashear Satellite1 — ver [wake-word-mariano.md §2–3](wake-word-mariano.md).

---

## Si el pod se para a mitad (saldo bajo)

Con **network volume** montado:

- RunPod **para** el pod si el saldo llega a $0
- Los datos en `/data` **se conservan** en el volume
- Recargas saldo, creas **otro pod** con el **mismo volume** en `/data` y reanudas (o relanzas el train si hace falta)

Sin volume, un pod terminado **pierde** el disco local.

---

## Checklist rápida

```
[ ] Auto-pay OFF · recarga $20–25 (o $50 techo)
[ ] Low balance alert $10
[ ] Volume 100 GB · anotado Volume ID · mismo datacenter que GPU
[ ] Pod on-demand Community · 1× GPU · imagen Tater · /data · :8789 · stop 48h
[ ] WAV en /data/personal_samples (~34)
[ ] train_wake_word Spanish mariano (tmux o UI)
[ ] mariano.tflite + mariano.json en ~/mww-runpod/trained_wake_words/
[ ] teardown_runpod_trainer.sh (stop) · --delete-volume si no re-entrenas
[ ] copy_model_from_trainer.sh
```

---

## Referencias

- [RunPod Pods pricing](https://docs.runpod.io/pods/pricing)
- [RunPod billing](https://docs.runpod.io/accounts-billing/billing)
- [Imagen Tater NVIDIA Docker](https://github.com/TaterTotterson/microWakeWord-Trainer-Nvidia-Docker)
- Runbook WayneHomeLab: [wake-word-mariano.md](wake-word-mariano.md)
