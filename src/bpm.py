"""
bpm.py - De las series RGB a la frecuencia cardíaca.

Método principal: POS (Plane-Orthogonal-to-Skin), Wang et al. (2017).
Método de comparación: canal verde normalizado y sin tendencia.

Por qué POS: el movimiento y los cambios de luz alteran el brillo de los tres
canales casi por igual (efecto "multiplicativo"), mientras que el pulso cambia
cada canal de forma distinta. POS proyecta las señales normalizadas sobre un
plano ortogonal a la dirección del brillo, y así cancela buena parte del ruido
común sin necesitar entrenamiento.
"""
import numpy as np

from .analysis import compute_spectrum, estimate_bpm_from_spectrum
from .config import BAND_HZ, POS_WINDOW_SECONDS
from .preprocessing import bandpass_filter, detrend_linear, normalize_by_mean

# Matriz de proyección de POS: filas = (G - B) y (-2R + G + B), con columnas (R, G, B).
_P = np.array([[0.0, 1.0, -1.0],
               [-2.0, 1.0, 1.0]])


def pos_algorithm(rgb, fs, window_seconds=POS_WINDOW_SECONDS):
    """
    Señal de pulso por POS con ventana deslizante y suma con solapamiento.

    En cada ventana de l muestras: (1) normalizar cada canal por su media local,
    (2) proyectar con _P, (3) combinar S1 + alpha*S2 con alpha = std(S1)/std(S2)
    (pondera para cancelar la componente común), (4) sumar a la salida.
    """
    rgb = np.asarray(rgb, dtype=float)
    n = rgb.shape[0]
    l = int(np.ceil(window_seconds * fs))
    if n < l:
        raise ValueError("La señal es más corta que la ventana de POS.")
    h_out = np.zeros(n)
    for m in range(0, n - l + 1):
        c = rgb[m:m + l].T                      # 3 x l
        cn = c / c.mean(axis=1, keepdims=True)  # normalización temporal
        s1, s2 = _P @ cn
        alpha = s1.std() / (s2.std() + 1e-12)
        h = s1 + alpha * s2
        h_out[m:m + l] += h - h.mean()
    return h_out


def green_channel_signal(rgb):
    """Método base de comparación: canal verde, variación relativa y sin tendencia."""
    return detrend_linear(normalize_by_mean(np.asarray(rgb)[:, 1]))


def estimate_bpm(rgb, fs, method="pos", use_bandpass=False, band=BAND_HZ):
    """Pipeline completo: serie RGB -> señal de pulso -> espectro -> BPM."""
    if method == "pos":
        pulse = pos_algorithm(rgb, fs)
    elif method == "green":
        pulse = green_channel_signal(rgb)
    else:
        raise ValueError("method debe ser 'pos' o 'green'")
    if use_bandpass:
        pulse = bandpass_filter(pulse, fs, band)
    freqs, magnitude = compute_spectrum(pulse, fs)
    est = estimate_bpm_from_spectrum(freqs, magnitude, band)
    est.update({"pulse": pulse, "freqs": freqs, "magnitude": magnitude, "method": method,
                "resolucion_bpm": 60.0 * fs / len(pulse)})
    return est
