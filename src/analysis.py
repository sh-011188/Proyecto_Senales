"""
analysis.py - Caracterización en el tiempo y análisis en frecuencia.

Qué calcula la FFT aquí: descompone la señal x[n] (N muestras, fs Hz) en
sinusoides. El eje horizontal es frecuencia en Hz (0 ... fs/2, el límite de
Nyquist); el vertical es la amplitud de cada sinusoide. Una frecuencia f en Hz
equivale a f*60 latidos por minuto (BPM).

Resolución espectral REAL: df = fs/N = 1/T (T = duración). Con T = 20 s,
df = 0.05 Hz = 3 BPM. El zero-padding interpola, pero no mejora esta resolución.
"""
import numpy as np
from scipy import signal

from .config import BAND_HZ, ZERO_PAD_FACTOR


def describe_signal(x, fs):
    """Características básicas de una señal discreta."""
    x = np.asarray(x, dtype=float)
    return {
        "n_muestras": int(len(x)),
        "fs_hz": float(fs),
        "Ts_s": float(1.0 / fs),
        "duracion_s": float(len(x) / fs),
        "minimo": float(x.min()),
        "maximo": float(x.max()),
        "amplitud_pico_a_pico": float(x.max() - x.min()),
        "media": float(x.mean()),
        "desv_estandar": float(x.std()),
    }


def compute_spectrum(x, fs, zero_pad_factor=ZERO_PAD_FACTOR, window="hann"):
    """
    Espectro de amplitud de un solo lado.

    Pasos: (1) quitar la media (si no, el pico en 0 Hz domina); (2) aplicar una
    ventana de Hann (reduce la fuga espectral por truncar la señal); (3) FFT con
    zero-padding; (4) escalar para que el pico dé ~ la amplitud de la sinusoide.
    """
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    w = signal.get_window(window, n)
    nfft = int(2 ** np.ceil(np.log2(n * zero_pad_factor)))
    spectrum = np.fft.rfft(x * w, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)
    magnitude = np.abs(spectrum) * 2.0 / np.sum(w)
    return freqs, magnitude


def estimate_bpm_from_spectrum(freqs, magnitude, band=BAND_HZ, half_width_hz=0.1):
    """
    Busca el pico dominante dentro de la banda fisiológica.

    quality = fracción de la potencia (en la banda) concentrada alrededor del
    pico (+/- half_width_hz). Es una HEURÍSTICA propia: cerca de 1 = un pico
    claro; valores bajos = espectro disperso/ruidoso, estimación poco confiable.
    """
    mask = (freqs >= band[0]) & (freqs <= band[1])
    f_band, m_band = freqs[mask], magnitude[mask]
    i = int(np.argmax(m_band))
    f_peak = float(f_band[i])
    power = m_band ** 2
    near = np.abs(f_band - f_peak) <= half_width_hz
    quality = float(power[near].sum() / power.sum())
    return {"bpm": f_peak * 60.0, "peak_hz": f_peak, "quality": quality}
