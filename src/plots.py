"""
plots.py - Gráficas con título, ejes y unidades (requisito de la entrega).

Cada función devuelve la figura y, si se da save_path, la guarda en disco.
"""
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from .config import BAND_HZ

CHANNEL_COLORS = {"R": "tab:red", "G": "tab:green", "B": "tab:blue"}


def _finish(fig, save_path):
    fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    return fig


def plot_frame_with_roi(frame_bgr, rois, face_box=None, masks=None, save_path=None):
    """
    Izquierda: fotograma con el rostro detectado (azul) y la(s) ROI (verde).
    Derecha: píxeles que realmente se promedian (máscara de piel); lo que queda en
    negro se excluye. Esta figura es la comprobación visual de que la ROI es buena.
    """
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [3, 2]})
    ax.imshow(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    if face_box is not None:
        x, y, w, h = face_box
        ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor="deepskyblue", lw=2,
                               label="Rostro detectado"))
    for i, (x, y, w, h) in enumerate(rois):
        ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor="lime", lw=2,
                               label="ROI de análisis" if i == 0 else None))
    ax.set_title("Fotograma de referencia y región de interés (ROI)")
    ax.set_xlabel("x (píxeles)")
    ax.set_ylabel("y (píxeles)")
    ax.legend(loc="lower right")

    masks = masks if masks is not None else [None] * len(rois)
    tiles = []
    for (x, y, w, h), m in zip(rois, masks):
        crop = cv2.cvtColor(frame_bgr[y:y + h, x:x + w], cv2.COLOR_BGR2RGB).copy()
        if m is not None:
            crop[m == 0] = 0
        tiles.append(cv2.resize(crop, (160, max(8, int(160 * h / w))), interpolation=cv2.INTER_NEAREST))
    ax2.imshow(np.vstack(tiles) if len(tiles) > 0 else np.zeros((10, 10, 3), np.uint8))
    ax2.set_title("Píxeles usados (negro = excluido)")
    ax2.axis("off")
    return _finish(fig, save_path)


def plot_rgb_time(t, rgb, title="Series temporales RGB promedio en la ROI", save_path=None):
    """R(t), G(t), B(t) en tres paneles (escalas distintas, porque la variación es pequeña)."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True)
    for ax, (i, name) in zip(axes, enumerate("RGB")):
        ax.plot(t, rgb[:, i], color=CHANNEL_COLORS[name], lw=1)
        ax.set_ylabel(f"{name} (nivel 0-255)")
        ax.grid(alpha=0.3)
    axes[0].set_title(title)
    axes[-1].set_xlabel("Tiempo (s)")
    return _finish(fig, save_path)


def plot_raw_vs_processed(t, raw, processed, label_raw="Canal G crudo",
                          label_proc="Normalizado y sin tendencia", save_path=None):
    """Señal original vs. la misma señal tras la primera etapa de procesamiento."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    axes[0].plot(t, raw, color="tab:green", lw=1)
    axes[0].set_ylabel("Nivel (0-255)")
    axes[0].set_title(label_raw)
    axes[1].plot(t, processed, color="tab:purple", lw=1)
    axes[1].set_ylabel("Variación relativa")
    axes[1].set_title(label_proc)
    axes[1].set_xlabel("Tiempo (s)")
    for ax in axes:
        ax.grid(alpha=0.3)
    return _finish(fig, save_path)


def plot_spectrum(freqs, magnitude, est, band=BAND_HZ, title="Espectro de amplitud",
                  true_bpm=None, save_path=None, fmax_hz=4.0):
    """Espectro con eje en Hz (abajo) y en BPM (arriba), banda fisiológica y pico."""
    fig, ax = plt.subplots(figsize=(10, 4))
    m = freqs <= fmax_hz
    ax.plot(freqs[m], magnitude[m], lw=1.2, color="tab:blue")
    ax.axvspan(band[0], band[1], color="gold", alpha=0.15, label="Banda fisiológica")
    ax.axvline(est["peak_hz"], color="crimson", ls="--",
               label=f"Pico: {est['peak_hz']:.2f} Hz = {est['bpm']:.1f} BPM")
    if true_bpm is not None:
        ax.axvline(true_bpm / 60.0, color="black", ls=":", label=f"Referencia: {true_bpm:.1f} BPM")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Amplitud (u. arb.)")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    top = ax.secondary_xaxis("top", functions=(lambda f: f * 60.0, lambda b: b / 60.0))
    top.set_xlabel("Equivalente en BPM")
    return _finish(fig, save_path)


def plot_simulation_overview(sim, save_path=None, window_s=8.0):
    """Pulso simulado (ventana) y BPM real instantáneo (verdad conocida)."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    k = int(window_s * sim["fs"])
    axes[0].plot(sim["t"][:k], sim["pulse"][:k], lw=1.2)
    axes[0].set_title(f"Pulso sintético s(t): primeros {window_s:.0f} s")
    axes[0].set_xlabel("Tiempo (s)")
    axes[0].set_ylabel("Amplitud normalizada")
    axes[1].plot(sim["t"], sim["bpm_true_t"], color="crimson")
    axes[1].set_title("Frecuencia cardíaca real instantánea (verdad conocida)")
    axes[1].set_xlabel("Tiempo (s)")
    axes[1].set_ylabel("BPM")
    for ax in axes:
        ax.grid(alpha=0.3)
    return _finish(fig, save_path)


def plot_pulse_signal(t, pulse, est, save_path=None, window_s=10.0):
    """
    Señal de pulso recuperada (POS) en el tiempo: una ventana de `window_s` s.
    Si el método funciona, se ven oscilaciones casi periódicas con periodo
    T0 = 1/f0 (f0 = pico del espectro), es decir, un "latido" por ciclo.
    """
    fig, ax = plt.subplots(figsize=(10, 3.6))
    k = min(len(t), int(window_s / (t[1] - t[0])) if len(t) > 1 else len(t))
    ax.plot(t[:k], pulse[:k], color="tab:purple", lw=1.2, label="Señal de pulso (POS)")
    if est.get("peak_hz"):
        t0 = 1.0 / est["peak_hz"]
        for tk in np.arange(0, t[k - 1], t0):
            ax.axvline(tk, color="crimson", alpha=0.15, lw=1)
        ax.plot([], [], color="crimson", alpha=0.4, label=f"Periodo estimado T0 = {t0:.2f} s")
    ax.set_title(f"Señal de pulso recuperada: primeros {t[k - 1]:.0f} s")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Amplitud (u. arb.)")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    return _finish(fig, save_path)


def plot_noise_comparison(t, clean, noisy, freqs, mag_clean, mag_noisy, est_clean, est_noisy,
                          snr_db, band=BAND_HZ, save_path=None, window_s=10.0, fmax_hz=4.0):
    """
    Ruido/degradación controlada: señal original vs. señal + ruido blanco gaussiano
    (SNR conocida), en el tiempo (arriba) y en frecuencia (abajo).
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5))
    k = min(len(t), int(window_s / (t[1] - t[0])) if len(t) > 1 else len(t))
    ax1.plot(t[:k], noisy[:k], color="tab:gray", lw=0.8, alpha=0.8, label=f"Con ruido (SNR = {snr_db:.0f} dB)")
    ax1.plot(t[:k], clean[:k], color="tab:green", lw=1.3, label="Original (G normalizado)")
    ax1.set_title("Ruido controlado en el tiempo")
    ax1.set_xlabel("Tiempo (s)")
    ax1.set_ylabel("Variación relativa")
    ax1.legend(loc="upper right")
    m = freqs <= fmax_hz
    ax2.plot(freqs[m], mag_noisy[m], color="tab:gray", lw=1, label=f"Con ruido: pico {est_noisy['bpm']:.1f} BPM")
    ax2.plot(freqs[m], mag_clean[m], color="tab:green", lw=1.3, label=f"Original: pico {est_clean['bpm']:.1f} BPM")
    ax2.axvspan(band[0], band[1], color="gold", alpha=0.15, label="Banda fisiológica")
    ax2.set_title("Efecto del ruido en el espectro")
    ax2.set_xlabel("Frecuencia (Hz)")
    ax2.set_ylabel("Amplitud (u. arb.)")
    ax2.legend(loc="upper right")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
    return _finish(fig, save_path)
