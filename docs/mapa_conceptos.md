# Mapa: concepto de Teoría de Señales -> dónde está en el proyecto

| Concepto | Dónde se usa | Evidencia (figura / salida) |
|---|---|---|
| Señal continua vs. discreta | Video = señal muestreada en el tiempo; `video_io.py`, `simulation.py` | Metadatos fs, Ts en web y terminal |
| Frecuencia y periodo de muestreo (fs, Ts) | `get_video_info`, `extract_rgb_series` | Tabla 1 de adquisición |
| Teorema de muestreo / Nyquist | fs = 30 Hz -> f_max = 15 Hz; banda fisiológica 0.7-3.0 Hz | Banda fisiológica en espectro |
| Aliasing | Parpadeo de luz física evaluado en instantes de muestreo | Simulación y documentación |
| Representación temporal | `plots.plot_rgb_time`, `plot_simulation_overview` | `results/*02_rgb_crudo.png` |
| Caracterización (mín, máx, media, std, N, duración, pico a pico) | `analysis.describe_signal` | Tabla 2 de caracterización |
| Periodicidad / periodo fundamental T0 | Forma de onda recuperada: T0 = 1/f0; `plot_pulse_signal` | `results/*06_pulso_pos.png` |
| Series de Fourier (armónicos) | Pulso periódico no senoidal con armónicos en 2*f0 | Espectro POS y detección de armónicos |
| Ruido y degradación | Ruido gaussiano del sensor, movimiento, iluminación | `results/*02_rgb_crudo.png` |
| Experimento de ruido controlado (SNR) | `preprocessing.add_white_noise` (SNR en dB, semilla fija) | `results/*07_ruido.png` |
| Cuantización | Redondeo a 8 bits (0-255) | `simulation.py`, series RGB |
| Normalización / detrending | `preprocessing.normalize_by_mean`, `detrend_linear` | `results/*03_preprocesado.png` |
| Ventaneo y fuga espectral | Ventana de Hann en `compute_spectrum` | Atenúa lóbulos laterales en FFT |
| FFT y espectro de amplitud unilateral | `analysis.compute_spectrum` | `results/*04_espectro_pos.png`, `*05_espectro_verde.png` |
| Resolución espectral y zero-padding | df = 1/T (real) vs. zero-padding (interpolación) | KPI en pantalla y reporte |
| Filtrado pasa banda | `bandpass_filter` (Butterworth orden 3, entrega final) | Checkbox interactivo en la web |
| Procesamiento multicanal | POS (Plane-Orthogonal-to-Skin) combina R, G, B | `bpm.pos_algorithm` |
| Interfaz gráfica de análisis | Servidor Flask + HTML/CSS/JS (`src/web_app.py`) | `http://127.0.0.1:5000` |

