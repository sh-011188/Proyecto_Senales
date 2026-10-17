"""
preprocessing.py - Primera etapa de procesamiento de la señal.

Operaciones (todas con sentido físico):
  - discard_start      : descarta los primeros segundos (auto-exposición de la cámara).
  - normalize_by_mean  : x/media - 1. Convierte la señal a variación RELATIVA
                         (parte AC / componente DC). Así los tres canales quedan
                         comparables y se reduce el efecto del brillo absoluto.
  - detrend_linear     : quita la tendencia lineal (deriva lenta).
  - bandpass_filter    : filtro Butterworth pasa banda de fase cero. OPCIONAL:
                         es contenido de la entrega final; por defecto no se usa.
"""
import numpy as np
from scipy import signal

from .config import BAND_HZ, BANDPASS_ORDER


def discard_start(t, rgb, fs, seconds):
    """Descarta los primeros `seconds` segundos."""
    k = int(round(seconds * fs))
    if k >= len(rgb) - 1:
        raise ValueError("El video es demasiado corto para descartar el inicio.")
    return t[k:] - t[k], rgb[k:]


def normalize_by_mean(x):
    """Variación relativa respecto a la media: x/mean(x) - 1."""
    x = np.asarray(x, dtype=float)
    return x / np.mean(x) - 1.0


def detrend_linear(x):
    """Quita la recta de mejor ajuste (mínimos cuadrados)."""
    return signal.detrend(np.asarray(x, dtype=float), type="linear")


def add_white_noise(x, snr_db, seed=0):
    """
    Degradación controlada: suma ruido blanco gaussiano con una SNR dada (dB).
    P_ruido = P_señal / 10^(SNR/10). Devuelve (señal_ruidosa, sigma_del_ruido).
    """
    x = np.asarray(x, dtype=float)
    p_signal = np.mean((x - x.mean()) ** 2)
    sigma = np.sqrt(p_signal / (10.0 ** (snr_db / 10.0)))
    rng = np.random.default_rng(seed)
    return x + rng.normal(0.0, sigma, size=x.shape), float(sigma)


def bandpass_filter(x, fs, band=BAND_HZ, order=BANDPASS_ORDER):
    """Butterworth pasa banda aplicado hacia adelante y hacia atrás (fase cero)."""
    nyq = fs / 2.0
    low, high = band
    if high >= nyq:
        raise ValueError(
            f"La banda {band} Hz excede Nyquist ({nyq:.2f} Hz) con fs={fs:.2f} Hz."
        )
    sos = signal.butter(order, [low / nyq, high / nyq], btype="bandpass", output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, dtype=float))
