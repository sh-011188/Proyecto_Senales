#!/usr/bin/env bash
# ==============================================================================
# Script para inicializar el repositorio Git con 6 commits organizados (2 personas x 3 commits)
# ==============================================================================
set -e

# Configuración de autores (puedes ajustar los correos si lo deseas)
NAME1="Juan Esteban Botero Sanchez"
EMAIL1="${1:-jbotero109535@umanizales.edu.co}"

NAME2="Salomé Granada Henao"
EMAIL2="${2:-sgranada111535@umanizales.edu.co}"

echo " Inicializando repositorio Git..."
if [ ! -d ".git" ]; then
  git init
fi

echo "--- Paquete 1/6 (Persona 1: $NAME1) ---"
git add .gitignore requirements.txt data/README.md data/.gitkeep src/__init__.py src/config.py src/video_io.py
GIT_AUTHOR_NAME="$NAME1" GIT_AUTHOR_EMAIL="$EMAIL1" \
GIT_COMMITTER_NAME="$NAME1" GIT_COMMITTER_EMAIL="$EMAIL1" \
git commit -m "feat(adquisicion): inicializar estructura del proyecto y modulo de muestreo temporal (fs, Ts)"

echo "--- Paquete 2/6 (Persona 2: $NAME2) ---"
git add src/roi.py src/signal_extraction.py docs/Especificaciones_Entrega_2_Teoria_Senales.pdf
GIT_AUTHOR_NAME="$NAME2" GIT_AUTHOR_EMAIL="$EMAIL2" \
GIT_COMMITTER_NAME="$NAME2" GIT_COMMITTER_EMAIL="$EMAIL2" \
git commit -m "feat(roi): implementar deteccion de rostro Haar, mascara YCrCb y extraccion de series RGB"

echo "--- Paquete 3/6 (Persona 1: $NAME1) ---"
git add src/preprocessing.py src/analysis.py
GIT_AUTHOR_NAME="$NAME1" GIT_AUTHOR_EMAIL="$EMAIL1" \
GIT_COMMITTER_NAME="$NAME1" GIT_COMMITTER_EMAIL="$EMAIL1" \
git commit -m "feat(procesamiento): agregar descarte de inicio, normalizacion AC/DC, detrending y caracterizacion estadistica"

echo "--- Paquete 4/6 (Persona 2: $NAME2) ---"
git add src/bpm.py src/plots.py src/report.py src/pipeline.py
GIT_AUTHOR_NAME="$NAME2" GIT_AUTHOR_EMAIL="$EMAIL2" \
GIT_COMMITTER_NAME="$NAME2" GIT_COMMITTER_EMAIL="$EMAIL2" \
git commit -m "feat(frecuencia): implementar algoritmo POS, analisis espectral con ventana Hann y generador de figuras con reporte"

echo "--- Paquete 5/6 (Persona 1: $NAME1) ---"
git add src/simulation.py src/run_demo.py notebooks/01_simulacion.ipynb notebooks/02_video_real.ipynb results/
GIT_AUTHOR_NAME="$NAME1" GIT_AUTHOR_EMAIL="$EMAIL1" \
GIT_COMMITTER_NAME="$NAME1" GIT_COMMITTER_EMAIL="$EMAIL1" \
git commit -m "feat(simulacion): incorporar generador sintético con verdad conocida, cuadernos de analisis y resultados base"

echo "--- Paquete 6/6 (Persona 2: $NAME2) ---"
git add src/web_app.py src/web/ docs/mapa_conceptos.md docs/guia_sustentacion.md docs/explicacion_detallada.md docs/paquetes_commits.md README.md
GIT_AUTHOR_NAME="$NAME2" GIT_AUTHOR_EMAIL="$EMAIL2" \
GIT_COMMITTER_NAME="$NAME2" GIT_COMMITTER_EMAIL="$EMAIL2" \
git commit -m "feat(ui): anadir interfaz web interactiva, soporte de modo dedo/linterna y documentacion completa de entrega"

echo " ¡Listo! Historial generado exitosamente:"
git log --graph --pretty=format:'%h - %an: %s (%cr)'
