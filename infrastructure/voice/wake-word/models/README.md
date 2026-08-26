# Copiar artefactos del trainer a este directorio tras entrenar.
#
# Windows / Docker (CPU en RX 6750 XT, o NVIDIA si la hay):
#   WAKEWORD_TRAINER_DATA_DIR=$HOME/mww-data \
#     ./infrastructure/voice/wake-word/copy_model_from_trainer.sh
#
# Mac (Apple Silicon trainer):
#   ./infrastructure/voice/wake-word/copy_model_from_trainer.sh
#   # o a mano:
#   cp ~/.taterwakewordtrainer/app/current/trained_wake_words/mariano.* \
#      infrastructure/voice/wake-word/models/
#
# Luego servir en LAN:
#   ./infrastructure/voice/wake-word/serve_model.sh
#
# Los archivos .tflite no se commitean (gitignore). Solo mariano.json.example como plantilla.
