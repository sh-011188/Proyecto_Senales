# Explicación detallada del proyecto rPPG

Este documento explica **todo lo que hace el código**, en orden, con ejemplos numéricos. Está escrito para estudiar con el repositorio abierto al lado.

> Uso educativo. Nada de este proyecto es una medición clínica ni un diagnóstico.

---

# PARTE A - Cómo estudiarlo (el método)

Leer el código de corrido no sirve: se siente que se entiende y en la sustentación se cae. Lo que funciona es esto:

1. **Primero la idea, luego el código.** Antes de abrir un archivo, explícate en voz alta qué entra y qué sale de esa etapa.
2. **Sigue una sola señal de principio a fin.** Corre `python -m src.run_demo --simulado` y, en un notebook, imprime la forma (`shape`) y las primeras 5 muestras después de cada etapa. Ver cómo cambian los números es lo que hace que el pipeline "caiga".
3. **Predice, luego verifica.** Antes de cambiar un parámetro (`duration`, `fs`, `motion_std`), escribe en papel qué esperas que pase. Si te equivocas, ahí está lo que aún no entiendes.
4. **Reconstruye una pieza desde cero.** Ejemplo mínimo, para convencerte de que la FFT hace lo que dices (pégalo en Colab):

```python
import numpy as np
fs = 30.0; t = np.arange(0, 20, 1/fs)
x = np.sin(2*np.pi*1.2*t)                 # senoide de 1.2 Hz = 72 BPM
X = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1/fs)
print(f[np.argmax(X)] * 60)               # debe imprimir ~72
```
5. **Enséñaselo a alguien** (o a una pared). Si no puedes explicar una función en 30 segundos sin mirar, no la entiendes todavía.
6. **Simula la sustentación.** Usa las preguntas de `guia_sustentacion.md` y respóndelas sin leer.

**Plan sugerido (5 sesiones de 1 a 2 horas):**

| Sesión | Qué hacer |
|---|---|
| 1 | Parte B (conceptos) completa. Haz el ejemplo de la FFT con la senoide. |
| 2 | Módulos `video_io`, `roi`, `signal_extraction`. Corre el pipeline y mira las figuras. |
| 3 | `preprocessing` y `analysis`: caracterización, FFT, ventana, resolución. |
| 4 | `simulation` y `bpm` (POS). Haz los ejercicios de la Parte E. |
| 5 | Sustentación simulada: responde las preguntas en voz alta y redacta las interpretaciones de las figuras. |

**Qué priorizar.** Lo que la entrega evalúa y debes dominar sí o sí: muestreo (fs, Ts), señal en el tiempo, caracterización, ruido, y la FFT básica con sus ejes. POS y la máscara de piel son métodos de la literatura: si no los alcanzas a dominar, di con honestidad que son "una primera aproximación tomada de Wang et al. (2017)" y explica la idea general. Eso es mejor que fingir.

Además, el documento aclara que no se espera que conozcas de antemano temas que aún no se han visto en clase (por ejemplo, filtros). En tu README di cuáles partes van adelantadas respecto al curso.

---

# PARTE B - Los conceptos, uno por uno

## B1. Qué es el pulso "visto" por una cámara
Cada latido empuja sangre a los vasos pequeños de la piel. La sangre absorbe luz (sobre todo verde, hacia 550 nm), así que durante el latido la piel refleja un poco menos de luz. El cambio es de ~1 % del nivel de brillo: invisible al ojo, pero medible si se promedia bien. Esa variación se repite con la frecuencia del corazón: 72 latidos por minuto = 1.2 veces por segundo = 1.2 Hz.

## B2. Un video es una señal muestreada
Una cámara toma fotogramas separados por un tiempo fijo.
- **fs** (frecuencia de muestreo) = fotogramas por segundo (FPS). Ejemplo: 30 Hz.
- **Ts = 1/fs** = tiempo entre muestras. Con fs = 30: Ts = 33.3 ms.
- La muestra k ocurre en **t_k = k · Ts**.

Convertimos cada fotograma en un número por canal (el promedio de color en la ROI). Así el video pasa a ser **tres señales discretas**: R[k], G[k], B[k].

## B3. Nyquist y aliasing
Con fs muestras por segundo solo se pueden representar frecuencias hasta **fs/2** (límite de Nyquist). Una frecuencia mayor "se pliega" y aparece como otra menor. Eso es el **aliasing**.

Fórmula: `f_alias = |f - fs · round(f / fs)|`.
- Ejemplo del proyecto: parpadeo de 100 Hz con fs = 30: round(100/30) = 3, entonces |100 - 90| = **10 Hz**. El parpadeo "aparece" en 10 Hz.
- Caso especial: 60 Hz con fs = 30: 60 es múltiplo exacto de 30, el alias cae en 0 Hz y la senoide se muestrea siempre en cruces por cero. Vale cero en todas las muestras. (Por eso mi notebook anterior no mostraba ningún ruido de parpadeo.)
- Para el pulso: el máximo es ~3 Hz, así que Nyquist exige fs > 6 Hz. Con 30 Hz sobra.

## B4. Dominio temporal vs. dominio de la frecuencia
Una señal se puede ver como valores en el tiempo o como suma de sinusoides de distintas frecuencias. La **FFT** (transformada rápida de Fourier) calcula esa descomposición. En el espectro: eje X = frecuencia (Hz), eje Y = cuánta amplitud tiene cada frecuencia. Un pulso regular produce un **pico** en su frecuencia. BPM = 60 · f.

Esto conecta con tus series de Fourier: el pulso real no es una senoide, tiene forma de onda, y toda onda periódica es una **suma de armónicos** (múltiplos de la frecuencia fundamental). Por eso en el espectro puede aparecer un pico pequeño al doble de la frecuencia del pulso. Si el pico más alto fuera ese armónico, la estimación saldría duplicada: es un error típico.

## B5. Resolución espectral (importante y la gente se confunde)
Con una señal de **T segundos** (N muestras), la FFT separa frecuencias con una resolución de **df = fs/N = 1/T**.
- T = 24 s: df = 0.0417 Hz = **2.5 BPM**.
- No puedes distinguir 72 de 73 BPM con 24 s de video.
- El **zero-padding** (añadir ceros al final) hace la curva más suave y ayuda a ubicar el pico, pero **no mejora** esta resolución. Es interpolación, no información nueva.
- Para duplicar la resolución necesitas duplicar la duración del video.

## B6. Ventaneo y fuga espectral
Al usar solo N muestras es como multiplicar la señal infinita por un rectángulo: los bordes abruptos "ensucian" el espectro (fuga espectral). La **ventana de Hann** suaviza los bordes hacia cero y reduce esa fuga, a cambio de un pico algo más ancho.

## B7. Ruido, normalización y cuantización
- **Ruido:** variaciones que no son el pulso: ruido del sensor (rápido, aleatorio), movimiento y cambios de luz (lentos), parpadeo de lámparas.
- **Cuantización:** una cámara guarda cada color en 8 bits, es decir, enteros de 0 a 255. Un cambio de 1.8 niveles (pulso sobre G ≈ 120) es chico frente al paso de 1 nivel. Por eso se promedian muchos píxeles: el ruido independiente hace que el promedio "recupere" fracciones de nivel.
- **Normalización `x/media - 1`:** convierte a variación relativa; así R, G y B quedan comparables sin importar el brillo absoluto.

---

# PARTE C - El código, módulo por módulo

Flujo general:

```
video -> info (fs) -> primeros fotogramas -> rostro -> ROI (+máscara de piel)
      -> promedio RGB por fotograma -> descartar inicio -> caracterizar
      -> POS -> FFT -> pico en 0.7-3 Hz -> BPM
```

## `config.py` - los números en un solo lugar
- `BAND_HZ = (0.7, 3.0)`: 42 a 180 BPM, el rango en que puede estar un pulso humano en esta aplicación.
- `POS_WINDOW_SECONDS = 1.6`: ventana de POS, valor sugerido por el artículo.
- `ZERO_PAD_FACTOR = 8`: relleno con ceros de la FFT.
- `DISCARD_SECONDS = 1.0`: se descarta el primer segundo.
- `MIN_DURATION_SECONDS = 10`: por debajo de esto se avisa que la resolución es baja.
- `ROI_FRACTIONS`: dónde está cada zona dentro de la caja del rostro, como fracciones de la caja. **Son un punto de partida**; hay que ajustarlos mirando la figura.

## `video_io.py` - leer el video
- `get_video_info`: abre el video y lee FPS, tamaño y número de fotogramas. Calcula Ts = 1/fps y la duración. Si el FPS no es válido, lanza error (sin fs no hay análisis posible).
- `read_first_frames(n=30)`: devuelve los primeros 30 fotogramas. Sirven para detectar el rostro.
- `iter_frames`: **generador** que entrega un fotograma a la vez. Se usa así porque un video de 30 s a 1080p ocuparía varios GB si se cargara completo.

*Supuesto a declarar:* el FPS reportado es constante. Algunos celulares graban con FPS variable y eso deformaría el eje de tiempo.

## `roi.py` - dónde medir
- `detect_face_box`: pasa el fotograma a escala de grises, ecualiza el contraste y aplica el detector de Haar de OpenCV. Si hay varios rostros, toma el más grande.
- `estimate_face_box`: detecta en los 30 fotogramas y toma la **mediana** de las cajas (resistente a una detección rara). Si no hay detecciones consistentes, lanza un error explicativo.
- `rois_from_face_box`: convierte la caja del rostro en rectángulos de análisis usando `ROI_FRACTIONS`.
  - `frente`: un rectángulo en la frente. `mejillas`: dos rectángulos. `rostro`: una zona amplia (incluye ojos y boca, más ruidosa).
- `validate_manual_roi`: para cuando el detector falla, permite dar (x, y, w, h) a mano y verifica que cabe en la imagen.
- `build_skin_masks`: convierte a YCrCb y conserva los píxeles con Cr entre 133-173 y Cb entre 77-127 (umbrales clásicos de piel). Luego limpia puntos sueltos. Si menos del 20 % de la ROI parece piel, descarta la máscara y avisa.

*Decisiones a poder justificar:* ROI fija (simple y estable, pero exige que la persona esté quieta); mediana de varias detecciones; la máscara sirve contra cejas, cabello oscuro o fondo. *Limitación real:* un cabello cuyo color se parece a la piel no se excluye (pasó en una prueba con cabello castaño claro).

## `signal_extraction.py` - de imagen a señal
`extract_rgb_series` recorre el video fotograma a fotograma. En cada uno, y para cada ROI, calcula el promedio de B, G, R **solo de los píxeles de la máscara** (si hay) con `cv2.mean`. Si hay varias ROI (mejillas), las combina ponderando por su número de píxeles. Devuelve:
- `rgb`: matriz N x 3 (columnas R, G, B),
- `t`: tiempos `k/fps`,
- `fs`.

OpenCV trabaja en orden **BGR**; por eso el código reordena a RGB.

## `preprocessing.py` - primera etapa de procesamiento
- `discard_start`: quita los primeros `fs · seconds` muestras. Razón física: al empezar a grabar, la cámara ajusta exposición y balance de blancos y el brillo cambia por razones que no son el pulso.
- `normalize_by_mean`: `x/media - 1`. Pasa de amplitudes absolutas a variación relativa AC/DC centrada en cero.
- `detrend_linear`: resta la recta de mejor ajuste (quita deriva lenta por movimiento o cambios lentos de iluminación).
- `add_white_noise`: experimento de degradación controlada (requisito 4.5 del proyecto). Suma ruido blanco gaussiano con una SNR fija dada en decibelios ($P_{\text{ruido}} = P_{\text{señal}} / 10^{\text{SNR}/10}$): permite verificar qué tan tolerante es el espectro ante pérdidas de calidad.
- `bandpass_filter`: filtro Butterworth pasa banda de orden 3 aplicado hacia adelante y hacia atrás (`sosfiltfilt`), lo que evita distorsión de fase. **Es opcional y no se usa por defecto**: los filtros son tema de la entrega final.

## `analysis.py` - caracterizar y pasar a frecuencia
- `describe_signal`: N, fs, Ts, duración, mínimo, máximo, pico a pico, media, desviación estándar. Es la "caracterización inicial" que pide la rúbrica.
- `compute_spectrum`, paso a paso:
  1. Resta la media (si no, el valor 0 Hz domina el espectro).
  2. Multiplica por la ventana de Hann (atenúa los bordes para evitar saltos artificiales).
  3. Rellena con ceros hasta la siguiente potencia de 2 de `N · 8`. Ejemplo: N = 720, 720·8 = 5760, y la potencia de 2 siguiente es 8192.
  4. Calcula la FFT de un solo lado (`rfft`) y las frecuencias asociadas (`rfftfreq`).
  5. Escala la magnitud con `2·|X| / suma(ventana)` para que el pico valga aproximadamente la amplitud de la sinusoide.
- `estimate_bpm_from_spectrum`: se queda con las frecuencias de 0.7 a 3 Hz, toma la de mayor amplitud y la multiplica por 60. Además calcula la **calidad**: la fracción de la potencia de esa banda que está a ±0.1 Hz del pico. Es una heurística propia: cerca de 1 = pico claro, valores bajos = espectro disperso. No es una probabilidad de acierto.

*Ejemplo numérico:* con N = 720 y zero-padding a 8192, el espaciado entre puntos del espectro es 30/8192 = 0.0037 Hz = 0.22 BPM. Eso es interpolación; la resolución real sigue siendo 2.5 BPM.

## `bpm.py` - POS
**Idea:** el movimiento y los cambios de luz alteran los tres canales casi **por igual** (cambia el brillo). El pulso, en cambio, afecta a cada canal de forma distinta. POS busca una combinación de canales que cancele lo común y conserve lo diferencial.

`pos_algorithm`, con fs = 30:
1. Ventana de `l = ceil(1.6·30) = 48` muestras (1.6 s).
2. Para cada posición de la ventana (avanzando de 1 en 1):
   - toma las muestras R, G, B de esa ventana y **divide cada canal por su media**;
   - calcula `S1 = G - B` y `S2 = -2R + G + B` (la matriz `_P`). Ambas combinaciones valen cero si los tres canales suben igual, es decir, no ven el cambio de brillo;
   - combina `h = S1 + α·S2` con `α = std(S1)/std(S2)`, que iguala las amplitudes para que el ruido restante se cancele mejor;
   - resta la media de `h` y la **suma** sobre las posiciones que cubre la ventana (suma con solapamiento).
3. El resultado es una señal de pulso con menos movimiento.

`green_channel_signal`: método base de comparación, solo el canal G normalizado y sin tendencia.

`estimate_bpm`: ejecuta el método elegido, opcionalmente aplica el pasa banda, calcula el espectro y el BPM. También devuelve la **resolución en BPM** (`60·fs/N`).

## `plots.py` - 7 figuras con título, ejes y unidades
Todas las gráficas llevan títulos claros y unidades legibles:
1. `plot_frame_with_roi`: rostro detectado, ROI y máscara de píxeles de piel utilizados.
2. `plot_rgb_time`: tres paneles con las señales $R(t), G(t), B(t)$ en el tiempo.
3. `plot_raw_vs_processed`: canal verde en nivel original (0-255) vs. variación relativa centrada en cero.
4. `plot_spectrum` (POS): espectro con eje dual (Hz abajo, BPM arriba), banda sombreada de 0.7-3 Hz y pico detectado.
5. `plot_spectrum` (Verde): espectro del canal verde base.
6. `plot_pulse_signal`: forma de onda en el tiempo de la señal de pulso recuperada, con líneas verticales espaciadas cada $T_0 = 1/f_0$ mostrando la periodicidad cardíaca.
7. `plot_noise_comparison`: comparación de la señal limpia vs. alterada con ruido blanco gaussiano (SNR conocida) tanto en el dominio del tiempo como en el de la frecuencia.

## `report.py` - interpretación física automática y reporte
La entrega pide explícitamente que cada figura tenga interpretación. `report.py` analiza numéricamente los resultados (deriva en niveles por segundo, amplitud relativa % sobre DC, detección de armónicos en $2\cdot f_0$, factor de calidad, y error contra la referencia) y genera:
- `reporte.md`: reporte completo en formato Markdown listo para pegar en el README o entrega.
- `resultados.json`: archivo estructurado con todos los valores numéricos calculados.

## `web_app.py` y `web/` - interfaz gráfica interactiva
Construido con Flask en el backend y una interfaz moderna en Vanilla HTML5/CSS3/JavaScript:
- **Carga de archivos sin límites de terceros**: El video se sube a `data/uploads/` y se procesa localmente en un hilo con `threading.Lock` para que Matplotlib no bloquee el servidor.
- **Barra de progreso reactiva**: Muestra en tiempo real qué etapa se está ejecutando (detección de rostro, extracción cuadro a cuadro, FFT, reporte).
- **Tarjetas y tablas dinámicas**: Muestra BPM, calidad, resolución $1/T$, error vs. pulso medido a mano, tabla de parámetros de muestreo ($f_s, T_s$, Nyquist, duración) y tabla de caracterización ($R, G, B$).
- **Visor interactivo con Lightbox**: Permite ampliar cualquiera de las 7 figuras y leer su interpretación física directamente en la web.
- **Descarga en 1 clic**: Botón para descargar el reporte Markdown, JSON o el paquete comprimido `.zip` con todas las figuras.

## `pipeline.py` y `run_demo.py`
`analyze_video` encadena todo: info -> primeros fotogramas -> ROI (manual o detectada) -> máscara -> figura de ROI -> extracción -> descartar inicio -> avisos -> figuras -> POS y verde -> espectros -> señal de pulso -> ruido controlado -> reporte automático e impreso en consola.
`run_demo.py` permite correr exactamente lo mismo desde la consola terminal (`--simulado`, `--video`, `--roi-mode`, `--roi`, `--esperado`).


---

# PARTE D - Qué significan los resultados

- **Pico del espectro** = frecuencia dominante dentro de 0.7 a 3 Hz. BPM = 60 × esa frecuencia.
- **Error** = BPM estimado - referencia. Compáralo con la **resolución** (≈ 2.5 BPM con 24 s): un error menor que eso está dentro de lo que el método puede distinguir.
- **Calidad baja** o varios picos del mismo tamaño = estimación poco confiable; revisa la ROI, el movimiento y la luz.
- **Tu referencia manual es aproximada** (contar pulsaciones a mano tiene su propio error, de unos pocos BPM). Una coincidencia "perfecta" no es el criterio; un acuerdo razonable sí.
- **En simulación** (semilla 42): real 72.20, POS 72.07, verde 72.29. Es un resultado en condiciones controladas, no una garantía para video real.

# PARTE E - Ejercicios (predice y luego verifica)

1. Pon `duration=10`: calcula antes la resolución en BPM. ¿Se vuelve más difícil distinguir 72 de 74?
2. Pon `fs=15`: usando la fórmula, ¿en qué frecuencia aliasa el parpadeo de 100 Hz? Compruébalo en el espectro crudo.
3. Pon `flicker_hz=60` con `fs=30`: ¿qué espectro esperas? ¿Por qué no aparece pico?
4. Sube `motion_std` a 0.05 y 0.1: ¿cuándo falla el canal verde? ¿Y POS?
5. Cambia `f0_mean` a 2.0 Hz (120 BPM). ¿Sigue estando el pico dentro de la banda? ¿Y un valor de 3.5 Hz?
6. En el video real, compara `frente`, `mejillas`, `rostro`. ¿Coinciden? ¿Cuál tiene mejor calidad?
7. Quita la ventana de Hann (llama a `compute_spectrum(x, fs, window="boxcar")` directamente): ¿cambia el aspecto del espectro?

# PARTE F - Glosario rápido

- **fs / FPS:** muestras (fotogramas) por segundo.
- **Ts:** tiempo entre muestras, 1/fs.
- **Nyquist:** frecuencia máxima representable, fs/2.
- **Aliasing:** frecuencia alta que aparece disfrazada de una baja por muestreo insuficiente.
- **ROI:** región de interés, la zona del rostro que se promedia.
- **FFT:** algoritmo rápido para calcular la descomposición en frecuencias.
- **Armónico:** múltiplo entero de la frecuencia fundamental.
- **Fuga espectral:** "derrame" de energía a frecuencias vecinas por truncar la señal.
- **Zero-padding:** añadir ceros para interpolar el espectro (no mejora la resolución).
- **POS:** método que combina R, G, B para cancelar el ruido común.
- **BPM:** latidos por minuto = 60 · frecuencia en Hz.
- **Ground truth:** valor real conocido, disponible en simulación.
