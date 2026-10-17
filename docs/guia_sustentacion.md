# Guía de estudio y sustentación

Este documento es para que puedas **explicar y defender** cada parte del proyecto. Léelo con el código al lado. Si algo del código no lo puedes explicar con tus palabras, cámbialo o simplifícalo: es mejor un método sencillo que entiendes que uno sofisticado que no.

> Uso educativo. Nada de este proyecto es una medición clínica ni un diagnóstico.

---

## 1. El proyecto en una frase

Cada latido cambia levemente cuánta luz absorbe la piel; una cámara registra ese cambio como una variación diminuta de color (~1 %), y con procesamiento de señales se recupera la frecuencia de esa variación, que es el pulso.

## 2. Flujo completo (aprende este orden)

```
video -> (fs = FPS) -> detectar rostro (Haar) -> ROI (frente) + máscara piel (YCrCb)
      -> promedio RGB por fotograma -> señales discretas R[k], G[k], B[k]
      -> descartar 1 s -> caracterización temporal (min, max, media, std, pico a pico)
      -> normalización (x/media - 1) + detrending lineal
      -> POS (combina canales) & canal verde base
      -> ventana Hann + FFT (zero-padding x8) -> pico en 0.7-3 Hz -> BPM = 60 * f0
      -> prueba de ruido controlado (SNR en dB)
      -> reporte automático e interfaz web (Flask + HTML/CSS/JS)
```

Orden recomendado para leer el código: `config.py` -> `video_io.py` -> `roi.py` -> `signal_extraction.py` -> `preprocessing.py` -> `analysis.py` -> `bpm.py` -> `plots.py` -> `report.py` -> `simulation.py` -> `pipeline.py` -> `web_app.py`.

## 3. Fórmulas que debes dominar

| Idea | Fórmula | Ejemplo |
|---|---|---|
| Periodo de muestreo | Ts = 1 / fs | fs = 30 Hz -> Ts = 33.3 ms |
| Tiempo de la muestra k | t_k = k · Ts | k = 30 -> t = 1.0 s |
| Frecuencia a BPM | BPM = 60 · f(Hz) | 1.25 Hz = 75 BPM |
| Periodo fundamental del latido | T0 = 1 / f0 | f0 = 1.25 Hz -> T0 = 0.8 s entre latidos |
| Límite de Nyquist | f_max representable = fs / 2 | 15 Hz con fs = 30 |
| Resolución espectral real | df = fs / N = 1 / T | T = 20 s -> df = 0.05 Hz = 3 BPM |
| Relación Señal a Ruido (SNR) | SNR(dB) = 10 · log10(P_señal / P_ruido) | 0 dB: ruido con la misma potencia que la señal |
| Aliasing | f_alias = abs(f - fs · round(f / fs)) | 100 Hz a fs = 30 -> 10 Hz |
| Variación relativa (AC/DC) | x / media(x) - 1 | Elimina el nivel DC y compara canales |
| POS (por ventana) | S1 = G - B ; S2 = -2R + G + B ; h = S1 + (std S1 / std S2) · S2 | tras normalizar cada canal |

## 4. Qué hace cada módulo y qué decir

**`video_io.py` - muestreo temporal.** Un video es una señal muestreada: fs = FPS. Se extraen fs y Ts porque todo el análisis en frecuencia depende de fs. *Limitación:* se asume FPS constante; algunos celulares graban con FPS variable y eso distorsiona el eje de tiempo.

**`roi.py` - dónde se mide.** El detector de rostros Haar (Viola y Jones, 2001) viene incluido en OpenCV (`<5.0`). Se detecta en los primeros 30 fotogramas y se usa la **mediana** de las cajas para tener una ROI estable y fija. La frente y las mejillas son zonas con buena perfusión y sin boca ni ojos (que se mueven). La **máscara de piel** (espacio YCrCb) descarta píxeles que no parecen piel. *Limitaciones:* la ROI fija exige que la persona esté quieta; la máscara no distingue un cabello cuyo color se parece al de la piel. Por eso existe la figura `01_roi.png`: **siempre se revisa a ojo**.

**`signal_extraction.py` - de imagen a señal.** Por cada fotograma se promedian los píxeles de piel en la ROI para obtener R[k], G[k], B[k]. Promediar N píxeles reduce el ruido espacial independiente ~ 1/sqrt(N) y permite medir variaciones inferiores a 1 nivel de cuantización de 8 bits.

**`preprocessing.py` - primera etapa de procesamiento.** Descartar el primer segundo (la cámara ajusta exposición y balance de blancos al iniciar). Normalizar `x/media - 1` pasa la señal a variación relativa AC/DC: quita el brillo absoluto y hace comparables los canales. Quitar tendencia lineal elimina deriva lenta. Además incluye la **prueba de degradación controlada (`add_white_noise`)**: suma ruido blanco gaussiano con una SNR conocida en dB para evaluar la resistencia del espectro.

**`analysis.py` - dominio temporal y frecuencial.** `describe_signal` da la caracterización completa (N, fs, duración, mínimo, máximo, media, desviación, amplitud pico a pico). `compute_spectrum`: resta la media, aplica ventana de Hann (reduce la **fuga espectral**), realiza FFT unilateral con zero-padding (x8) y escala la amplitud. `estimate_bpm_from_spectrum` busca el pico **solo en 0.7-3 Hz** (42-180 BPM, rango fisiológico). La "calidad" mide la fracción de potencia concentrada alrededor del pico.

**`bpm.py` - POS y Verde.** El movimiento y la luz cambian los tres canales casi por igual (efecto multiplicativo), mientras el pulso los cambia distinto. POS normaliza cada canal por su media local, proyecta sobre dos direcciones ortogonales a la dirección del brillo y las combina con un peso que equilibra amplitudes. Resultado: una señal de pulso con menos movimiento. Se compara contra el canal verde solo (método base).

**`plots.py` y `report.py` - figuras e interpretación.** Generan 7 figuras completas con ejes físicos, títulos y unidades, más un archivo `reporte.md` y `resultados.json` que explican físicamente lo observado en cada gráfica (requisito explícito de la entrega).

**`web_app.py` - interfaz web interactiva.** Servidor local Flask que permite arrastrar el video, configurar la ROI y el pulso esperado, y visualizar los resultados (BPM, tablas, gráficas e interpretaciones) de forma accesible.

**`simulation.py` - verdad conocida.** Pulso con armónicos, respiración (RSA), ruido gaussiano, movimiento multiplicativo (Ornstein-Uhlenbeck), parpadeo y cuantización a 8 bits. Permite medir el error contra el BPM real con total reproducibilidad.

## 5. Preguntas probables y cómo responderlas

1. **¿Por qué video y no una imagen?** El pulso es una variación en el tiempo; una foto es un solo instante y no contiene esa variación temporal.
2. **¿Por qué el canal verde?** La hemoglobina tiene su pico de absorción óptica cerca de los 550 nm (luz verde), por lo que el canal verde presenta la mayor amplitud pulsátil. Sin embargo, combinar canales (POS) es más robusto ante cambios de iluminación.
3. **¿Cuál es fs y por qué sirve 30 Hz?** fs = FPS del video. La frecuencia cardíaca máxima de interés es 3 Hz (180 BPM). El teorema de Nyquist exige fs > 2 · 3 Hz = 6 Hz; 30 Hz cumple holgadamente y captura hasta el 5to armónico.
4. **¿Qué es la resolución espectral?** df = 1/T. Con un video de 20 s de duración útil, df = 0.05 Hz = 3 BPM. No se puede distinguir 72 de 73 BPM con tan poco video. El zero-padding interpola la curva para localizar el pico, pero **no** mejora esta resolución física.
5. **¿Para qué la ventana de Hann?** Truncar la señal en N muestras equivale a multiplicarla por una ventana rectangular, cuyos lóbulos laterales dispersan energía a otras frecuencias (fuga espectral). Hann atenúa suavemente los extremos a cero, reduciendo la fuga.
6. **¿Qué es el aliasing? Dame un ejemplo del proyecto.** Cuando una componente tiene frecuencia mayor a fs/2, se pliega hacia frecuencias bajas. Un parpadeo de red eléctrica de 100 Hz muestreado a 30 Hz genera un alias en |100 - 3 · 30| = 10 Hz.
7. **¿Por qué buscar el pico solo entre 0.7 y 3 Hz?** Fuera de esa banda no hay pulso humano fisiológicamente normal (42 a 180 BPM); dejar abierta la búsqueda haría que componentes de muy baja frecuencia (deriva o movimiento) ganen el máximo erróneamente.
8. **¿Qué representa la figura de ruido controlado (07_ruido)?** Evaluamos cómo afecta una degradación conocida (ruido blanco con SNR = 0 dB). En el tiempo la onda se vuelve casi irreconocible, pero en el espectro el pico cardíaco aún puede sobresalir si la potencia del pulso está concentrada en una sola frecuencia.
9. **¿Qué representa el periodo fundamental T0 en la figura 06_pulso_pos?** El inverso del pico espectral T0 = 1/f0 es el periodo medio de cada latido (ej. 0.8 s para 75 BPM). Las líneas verticales muestran cómo los ciclos del pulso recuperado en el tiempo coinciden con ese espaciamiento periódico.
10. **¿Cómo validan sin un sensor médico?** (a) Con la simulación y video sintético, donde el BPM real se conoce de forma exacta. (b) Con el video de prueba, comparándolo contra la medición manual de pulso en el cuello tomada durante la grabación (referencia aproximada declarada).
11. **¿Por qué se descarta el primer segundo?** La cámara del celular realiza ajustes automáticos de ganancia, exposición y balance de blancos al empezar a grabar, lo que genera saltos bruscos que distorsionan el espectro.
12. **¿Es un dato clínico?** No. Es un ejercicio educativo de procesamiento de señales rPPG. No tiene validez médica ni diagnóstica.
13. **¿Qué falta para la entrega final?** Filtro pasa banda completo con diseño y análisis de respuesta en frecuencia, estimación de BPM instantáneo con ventanas deslizantes (STFT/espectrograma), y comparación sistemática entre diferentes condiciones de iluminación y sujetos.

## 6. Qué NO debes afirmar

- Que el sistema "evalúa la salud del corazón" o detecta enfermedades.
- Que tiene precisión clínica o validación médica.
- Que POS es siempre mejor que el canal verde.
- Que la calidad (heurística) es una probabilidad de acierto.

## 7. Qué se probó y qué no (honestidad sobre el estado real)

Se probó con: (a) señales simuladas (muchas semillas), (b) un video sintético generado por el código, y (c) un video construido a partir de una foto de archivo (dominio público) modulada artificialmente a 72 BPM, para comprobar la detección de rostro y la ROI. **No se probó con un video de una persona real**: ese resultado lo tienes que obtener y documentar tú, y puede ser peor que en la simulación.

## 8. Ejercicios para entender (predice, luego verifica)

1. En `simulate_rgb`, pon `duration=10`. ¿Qué pasa con la resolución en BPM? Calcúlala antes de correr.
2. Pon `fs=15`. ¿Dónde aliasa un parpadeo de 100 Hz? (usa la fórmula de aliasing y compara con el espectro)
3. Sube `motion_std` a 0.05 y 0.1. ¿Cuándo empieza a fallar el canal verde? ¿Y POS?
4. Pon `flicker_hz=60` con `fs=30`. ¿Qué espectro esperas? ¿Por qué?
5. En un video real, compara `frente`, `mejillas` y `rostro`. ¿Coinciden? ¿Cuál tiene mejor calidad y por qué crees que es?
