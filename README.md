# Estimación de la frecuencia cardíaca mediante video (rPPG)

**Curso:** Teoría de Señales - Proyecto 9 (segunda entrega)
**Integrantes:** Juan Esteban Botero Sanchez (`jbotero109535@umanizales.edu.co`) y Salomé Granada Henao (`sgranada111535@umanizales.edu.co`)

> **Uso educativo. No es una medición clínica ni diagnóstica.**

## 1. Descripción y Principio Físico
Cada latido del corazón bombea sangre rica en hemoglobina hacia los capilares sanguíneos de la piel. La hemoglobina absorbe luz (con un pico pronunciado cerca de los 550 nm, luz verde). Una cámara de video convencional registra estas variaciones diminutas de absorción óptica como fluctuaciones de color (~1 % de variación en el rostro, o ~5-15 % si se apoya el dedo sobre el lente con la linterna encendida).

El sistema procesa el video como una **señal discreta en el tiempo**, promedia espacialmente los píxeles de piel para reducir el ruido del sensor a razón de $1/\sqrt{N}$, acondiciona la señal temporal, calcula su espectro de amplitud mediante la **Transformada Rápida de Fourier (FFT)** y estima la frecuencia cardíaca (BPM) a partir del pico espectral dominante dentro de la banda fisiológica humana ($0.7 \text{ a } 3.0 \text{ Hz}$, equivalente a $42 \text{ a } 180 \text{ BPM}$).

Además, se incluye una **simulación con verdad conocida** y un video sintético reproducible para validar matemáticamente la exactitud del método sin necesidad de una persona ni de sensores médicos.

## 2. Estado actual
**Funciona:**
- Lectura de video y documentación formal de frecuencia de muestreo $f_s$ (FPS) y periodo de muestreo $T_s = 1/f_s$.
- Dos modalidades de captura:
  1. **Rostro sin contacto (rPPG):** Detección automática del rostro con clasificador Haar (Viola-Jones), segmentación de regiones ROI (frente, mejillas o rostro completo) y máscara de piel en espacio cromático $Y\text{CrCb}$.
  2. **Dedo en la cámara (PPG por contacto):** Apoyando la yema del dedo sobre el lente del celular con la linterna (flash) encendida, analizando la zona central sin requerir rostro.
- Extracción de series temporales discretas $R[k], G[k], B[k]$ y caracterización estadística ($N$, $f_s$, duración, mínimo, máximo, media, desviación estándar $\sigma$ y amplitud pico a pico).
- Primera etapa de procesamiento: descarte del primer segundo (ajuste automático de exposición de cámara), normalización por la media ($x/\bar{x} - 1$, relación AC/DC) y eliminación de tendencia lineal (*detrending*).
- Análisis en frecuencia: enventanado de Hann (atenuación de fuga espectral), zero-padding (x8) y estimación de BPM mediante el algoritmo **POS** (*Plane-Orthogonal-to-Skin*, Wang et al., 2017) y con el **Canal Verde** (método base).
- Experimento de degradación controlada: suma de ruido blanco gaussiano con relación señal a ruido (SNR) configurable en dB y semilla fija reproducible.
- **Interfaz web interactiva local:** permite cargar el video en el navegador, ver el progreso paso a paso, visualizar las 7 figuras con interpretación física automática y descargar el reporte completo en Markdown (`reporte.md`), JSON o `.zip`.

**Falta (para la entrega final):** Filtro digital pasa banda definitivo con diseño y análisis de respuesta en frecuencia, estimación de frecuencia cardíaca instantánea mediante ventanas deslizantes (STFT / espectrograma), y validación sistemática con múltiples sujetos e iluminaciones.

## 3. Datos o recursos
- **Señal simulada:** generada computacionalmente (`src/simulation.py`, semilla fija 42). Es completamente reproducible y no requiere descargas.
- **Detector de rostros:** clasificador Haar frontal incluido nativamente en OpenCV (Viola y Jones, 2001).
- **Video propio:** video corto grabado con celular o cámara (ver recomendaciones de grabación más abajo).

---

## 4. Cómo clonar y ejecutar (Guía Paso a Paso)

### Paso 1: Descargar el proyecto
Puedes clonar el repositorio o descargarlo como archivo ZIP:

* **Opción con Git (Terminal):**
  ```bash
  git clone https://github.com/sh-011188/Proyecto_Senales.git
  cd Proyecto_Senales
  ```
* **Opción sin Git (Descarga directa):**
  1. Entra a [https://github.com/sh-011188/Proyecto_Senales](https://github.com/sh-011188/Proyecto_Senales).
  2. Haz clic en el botón verde **Code** y selecciona **Download ZIP**.
  3. Descomprime el archivo en tu computadora y abre una terminal dentro de la carpeta descomprimida.

---

### Paso 2: Configuración del Entorno Virtual (Python 3.10+)

En tu terminal (dentro de la carpeta del proyecto):

```bash
# 1. Crear el entorno virtual
python -m venv .venv

# 2. Activar el entorno virtual:
# En Linux / macOS:
source .venv/bin/activate

# En Windows (Símbolo del sistema / CMD):
.venv\Scripts\activate

# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Nota: Si PowerShell muestra error de permisos de scripts, ejecuta antes:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Instalar dependencias (solo tarda unos segundos):
pip install -r requirements.txt
```

---

### Opción A (Recomendada): Interfaz Web Local
Es la forma más cómoda y visual de probar el proyecto:

1. **Iniciar la aplicación:**
   ```bash
   python -m src.web_app
   ```
   *(El sistema abrirá automáticamente tu navegador en **`http://127.0.0.1:5000`**).*

2. **Cómo usar la página:**
   - **Cargar el video:** Arrastra tu archivo de video (`.mp4`, `.mov`, `.avi`, etc.) o haz clic en el recuadro para seleccionarlo.
   - **Seleccionar Modalidad / ROI:**
     - `Frente` / `Mejillas`: Para videos del rostro (rPPG sin contacto).
     - `Dedo / Linterna`: Para videos apoyando la yema sobre la cámara con flash/linterna *(el sistema también cuenta con auto-detección inteligente)*.
   - **Referencia manual (opcional):** Si mediste tus pulsaciones en el cuello o muñeca (ej. 72), escríbelo en la casilla para calcular el error exacto.
   - **Analizar:** Haz clic en el botón **"Analizar video"**.
   - **Modo Demo sin cámara:** También puedes presionar el botón **"Probar con video sintético"** para ver todo el flujo con una señal sintética de verdad conocida (~72 BPM).

3. **Para detener / cerrar la página web:**
   - En la terminal donde la iniciaste, presiona **`Ctrl + C`**.

---

### Opción B: Ejecución por Terminal (Línea de Comandos)
También puedes ejecutar el pipeline completo directamente desde la consola:

```bash
# 1. Prueba de simulación (genera video sintético y evalúa error vs. BPM real):
python -m src.run_demo --simulado

# 2. Video real de rostro (ROI en la frente por defecto):
python -m src.run_demo --video data/mi_video.mp4 --esperado 72

# 3. Video real de rostro seleccionando mejillas:
python -m src.run_demo --video data/mi_video.mp4 --roi-mode mejillas

# 4. Video del dedo sobre la cámara (con flash):
python -m src.run_demo --video data/mi_dedo.mp4 --roi-mode dedo

# 5. ROI manual en píxeles (x y ancho alto):
python -m src.run_demo --video data/mi_video.mp4 --roi 120 40 100 40
```
*Todas las figuras y el archivo `reporte.md` se guardan automáticamente en la carpeta `results/`.*

---

### Opción C: Google Colab
Si prefieres ejecutar en la nube:
1. Sube tu repositorio a GitHub.
2. Abre el cuaderno `notebooks/02_video_real.ipynb` (o `01_simulacion.ipynb`).
3. En la primera celda, escribe la URL de tu repositorio de GitHub y ejecuta las celdas en orden (en Colab el cuaderno te pedirá subir el video).

---

### Flujo de Procesamiento de la Señal
```text
Video (.mp4) 
   │
   ├─► 1. video_io.py: Muestreo temporal ──► fs = FPS, Ts = 1/fs
   │
   ├─► 2. roi.py: Detección facial (Haar) ──► ROI + Máscara de piel (YCrCb)
   │
   ├─► 3. signal_extraction.py: Promedio espacial ──► Series discretas R[k], G[k], B[k]
   │
   ├─► 4. preprocessing.py: Acondicionamiento ──► Descarte 1 s, AC/DC (x/media - 1), Detrending
   │
   ├─► 5. bpm.py: Algoritmo POS ──► Proyección ortogonal al brillo + Canal Verde
   │
   ├─► 6. analysis.py: Análisis espectral ──► Ventana Hann + FFT (zero-pad) ──► Pico f0 en [0.7, 3.0] Hz
   │
   └─► 7. report.py & plots.py: Resultados ──► BPM = 60 · f0, 7 figuras e interpretaciones
```

## 5. Conceptos de Teoría de Señales utilizados
Muestreo (fs, Ts) y Nyquist; aliasing; señal discreta; representación temporal; caracterización; periodicidad y series de Fourier (armónicos del pulso); ruido y cuantización; normalización y detrending; ventaneo y fuga espectral; FFT, resolución espectral y zero-padding. Detalle en `docs/mapa_conceptos.md`.

## 6. Resultados actuales
**Simulación** (semilla 42, reproducible con `python -m src.run_demo --simulado`): BPM real 72.20; POS 72.07 (error -0.13); canal verde 72.29 (error +0.09); resolución espectral de ±1 BPM aprox.

- `results/sim_01_pulso_y_verdad.png`: pulso sintético y BPM real instantáneo.
- `results/sim_02_rgb.png`: series RGB simuladas.
- `results/sim_03_espectro_pos.png`: espectro con el pico en el BPM real.

**Video sintético** (`results/simvideo_*.png`, ver `results/simvideo_reporte.md`): ROI, series RGB crudas, preprocesado, espectros POS y verde, señal de pulso recuperada y experimento de ruido controlado, cada una con su interpretación.

**Video real:** `[COMPLETAR: subir el video en la interfaz web, copiar aquí las figuras de results/web/<carpeta>/ y revisar/ajustar el texto de reporte.md]`.

| Figura | Qué muestra |
|---|---|
| `01_roi.png` | Fotograma con rostro detectado, ROI y píxeles de piel usados |
| `02_rgb_crudo.png` | Representación temporal R(t), G(t), B(t) |
| `03_preprocesado.png` | G crudo vs. normalizado y sin tendencia |
| `04_espectro_pos.png` | Espectro de la señal POS, pico = BPM |
| `05_espectro_verde.png` | Espectro del canal verde (método base) |
| `06_pulso_pos.png` | Forma de onda del pulso recuperado y periodo T0 |
| `07_ruido.png` | Señal original vs. con ruido (SNR conocida) en tiempo y frecuencia |

> Las figuras sin interpretación no cuentan: el `reporte.md` trae un borrador automático que deben revisar y completar con lo que observan.

## 7. Estructura
```
src/        código
  video_io, roi, signal_extraction, preprocessing, analysis, bpm   -> etapas del procesamiento
  simulation                                                       -> señal/video sintético con verdad conocida
  plots, report                                                    -> figuras e interpretación automática
  pipeline                                                         -> une todas las etapas (analyze_video)
  run_demo.py                                                      -> uso por terminal
  web_app.py + web/                                                -> interfaz web local (Flask + HTML/CSS/JS)
notebooks/  01_simulacion.ipynb, 02_video_real.ipynb (Colab)
data/       muestras de datos (ver data/README.md)
results/    figuras y reportes
docs/       especificaciones, guia_sustentacion.md, mapa_conceptos.md, explicacion_detallada.md, paquetes_commits.md
```

## 8. Referencias
- Verkruysse, W., Svaasand, L. O., & Nelson, J. S. (2008). Remote plethysmographic imaging using ambient light. *Optics Express*, 16(26), 21434-21445.
- Poh, M.-Z., McDuff, D. J., & Picard, R. W. (2010). Non-contact, automated cardiac pulse measurements using video imaging and blind source separation. *Optics Express*, 18(10), 10762-10774.
- de Haan, G., & Jeanne, V. (2013). Robust pulse rate from chrominance-based rPPG. *IEEE Transactions on Biomedical Engineering*, 60(10), 2878-2886.
- Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017). Algorithmic principles of remote PPG. *IEEE Transactions on Biomedical Engineering*, 64(7), 1479-1491.
- Viola, P., & Jones, M. (2001). Rapid object detection using a boosted cascade of simple features. *CVPR*.
- Chai, D., & Ngan, K. N. (1999). Face segmentation using skin-color map in videophone applications. *IEEE Trans. Circuits and Systems for Video Technology*, 9(4), 551-564.
