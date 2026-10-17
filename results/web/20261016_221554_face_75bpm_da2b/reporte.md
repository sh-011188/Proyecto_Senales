# Reporte rPPG - 20261016_221554_face_75bpm.mp4

> Uso educativo. No es una medición clínica ni diagnóstica.

**Resumen:** BPM estimado (POS): 75.1 ± 1.6 BPM, confiabilidad alta. Canal verde: 74.9 BPM. Referencia manual 75.0 BPM → error POS +0.1, verde -0.1 BPM.

## Adquisición

| Parámetro | Valor |
|---|---|
| fs = FPS | 30.000 Hz |
| Ts = 1/fs | 33.33 ms |
| Resolución | 640 × 480 px |
| Fotogramas | 600 |
| Duración total / útil | 20.0 s / 19.0 s |
| Nyquist fs/2 | 15.00 Hz |
| Resolución espectral 1/T | 3.16 BPM |

## Caracterización de las series R, G, B (niveles 0-255)

| Canal | N | mín | máx | pico a pico | media | desv. est. |
|---|---|---|---|---|---|---|
| R | 570 | 171.56 | 177.75 | 6.19 | 174.86 | 1.565 |
| G | 570 | 133.22 | 138.89 | 5.67 | 136.30 | 1.440 |
| B | 570 | 113.19 | 117.54 | 4.35 | 115.65 | 1.040 |

## 1. Región de interés (ROI)

![1. Región de interés (ROI)](01_roi.png)

La ROI se ubicó automáticamente en la zona «frente» a partir del rostro detectado con el clasificador Haar (Viola-Jones). Se usan 1 región(es) y la máscara de piel (espacio YCrCb) conserva 98 % de los píxeles. Solo se promedian píxeles de piel: cabello, cejas y fondo no contienen pulso y agregarían ruido. Verifique en la figura que el recuadro verde cae sobre piel.

## 2. Representación temporal: series R, G, B

![2. Representación temporal: series R, G, B](02_rgb_crudo.png)

Señal discreta muestreada a fs = 30.00 Hz (Ts = 33.3 ms), N = 570 muestras, duración útil 19.0 s (se descartaron los primeros 1.0 s por la auto-exposición). Niveles medios: R = 174.9, G = 136.3, B = 115.7 (escala 0-255). La variación pico a pico es pequeña respecto al nivel medio (R 3.5 %, G 4.2 %, B 3.8 %): el pulso es una variación de ~1 % montada sobre una componente DC grande. Deriva lenta a lo largo del video: R -1.80, G -1.44, B -1.11 niveles (cambios de luz o movimiento). Los saltos bruscos, si aparecen, suelen ser movimientos o ajustes de exposición.

## 3. Primera etapa de procesamiento

![3. Primera etapa de procesamiento](03_preprocesado.png)

Se normalizó el canal verde por su media (x/media − 1, es decir AC/DC) y se quitó la tendencia lineal. La señal pasa de niveles absolutos (~136) a variación relativa centrada en cero (desviación ≈ 1.06 %). Así los canales son comparables, se elimina la componente DC (que dominaría el espectro en 0 Hz) y la deriva de -1.44 niveles.

## 4. Análisis frecuencial (POS)

![4. Análisis frecuencial (POS)](04_espectro_pos.png)

La FFT (ventana de Hann, zero-padding ×8) muestra el contenido en frecuencia de la señal POS. Eje x: frecuencia en Hz (arriba en BPM = Hz × 60), de 0 a fs/2 = 15.0 Hz (Nyquist). Dentro de la banda fisiológica 0.7-3.0 Hz el pico dominante está en f0 = 1.252 Hz → 75.1 BPM. Calidad del pico 0.69 (confiabilidad alta). Resolución espectral real Δf = 1/T = 0.053 Hz ≈ 3.2 BPM: el zero-padding solo interpola, no mejora este límite. En 2·f0 = 2.50 Hz hay una componente de 48 % de la amplitud del pico (armónico: el pulso es periódico pero no senoidal, serie de Fourier).

## 5. Análisis frecuencial (canal verde)

![5. Análisis frecuencial (canal verde)](05_espectro_verde.png)

Con solo el canal verde (método base) el pico está en 1.249 Hz → 74.9 BPM (calidad 0.89). Diferencia con POS: -0.2 BPM; los dos métodos coinciden dentro de la resolución espectral, lo que da más confianza en la estimación. El verde es el canal más sensible a la hemoglobina; POS combina R, G y B para cancelar las variaciones de brillo comunes a los tres canales.

## 6. Señal de pulso recuperada

![6. Señal de pulso recuperada](06_pulso_pos.png)

Forma de onda de la señal de pulso extraída con POS. Las líneas rojas marcan el periodo estimado T0 = 1/f0 = 0.80 s; en 10 s caben ≈ 13 ciclos. Si las oscilaciones siguen las líneas, la señal es casi periódica y el pico espectral corresponde a los latidos. Variaciones de amplitud o ciclos irregulares indican ruido residual o variación natural del ritmo (respiración).

## 7. Ruido / degradación controlada

![7. Ruido / degradación controlada](07_ruido.png)

Se sumó ruido blanco gaussiano a la señal G normalizada con SNR = 0 dB (σ = 1.01e-02, semilla 0). En el tiempo la forma del pulso se vuelve difícil de ver; en frecuencia el ruido blanco se reparte en todas las frecuencias y levanta el piso del espectro. El pico pasa de 74.9 a 74.9 BPM (+0.0) y la calidad de 0.89 a 0.77. Ruidos reales que afectan la señal: ruido del sensor y de cuantización (8 bits), compresión del video, movimiento de la cabeza, cambios y parpadeo de la iluminación (aliasing si la luz parpadea por encima de fs/2).
