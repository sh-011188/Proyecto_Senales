"""
config.py - Parámetros globales del proyecto.

Todo número "mágico" vive aquí, con su justificación, para poder
explicarlo en la sustentación y cambiarlo en un solo lugar.
"""

# Banda fisiológica de la frecuencia cardíaca (en Hz).
# 0.7 Hz = 42 BPM (bradicardia profunda) ... 3.0 Hz = 180 BPM (esfuerzo alto).
BAND_HZ = (0.7, 3.0)

# Ventana del algoritmo POS, en segundos (valor recomendado por Wang et al., 2017:
# ~1.6 s, es decir, un poco más que un latido típico).
POS_WINDOW_SECONDS = 1.6

# Relleno con ceros (zero-padding) para la FFT: interpola el espectro para
# localizar mejor el pico. OJO: NO mejora la resolución real (eso lo fija la duración).
ZERO_PAD_FACTOR = 8

# Orden del filtro Butterworth pasa banda (uso opcional, tema de entrega final).
BANDPASS_ORDER = 3

# Cuántos fotogramas iniciales se usan para detectar el rostro.
FACE_DETECT_FRAMES = 30

# Segundos iniciales que se descartan: las cámaras de celular ajustan exposición
# y balance de blancos al empezar a grabar, y eso contamina la señal.
DISCARD_SECONDS = 1.0

# Duración mínima recomendada del video (s). Resolución espectral = 1/T.
MIN_DURATION_SECONDS = 10.0

# Ruido controlado (requisito 4.5 de la entrega): a la señal del canal verde ya
# normalizada se le suma ruido blanco gaussiano con esta relación señal/ruido.
# SNR (dB) = 10*log10(P_señal / P_ruido). 0 dB = ruido con la misma potencia que la señal.
NOISE_SNR_DB = 0.0
NOISE_SEED = 0          # semilla fija -> experimento reproducible

# Zonas de interés (ROI) como fracciones del cuadro del rostro detectado:
# (x_rel, y_rel, ancho_rel, alto_rel). Estos valores son un punto de partida:
# la caja del detector cambia según la persona y el peinado, así que SIEMPRE hay que
# mirar la figura 01_roi.png y ajustarlos (o usar manual_roi) si la ROI toca cabello o cejas.
ROI_FRACTIONS = {
    "frente":   [(0.25, 0.22, 0.50, 0.18)],
    "mejillas": [(0.12, 0.55, 0.25, 0.20), (0.63, 0.55, 0.25, 0.20)],
    "rostro":   [(0.15, 0.15, 0.70, 0.75)],
}
