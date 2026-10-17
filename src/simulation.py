"""
simulation.py - Generador de señales rPPG sintéticas (con verdad conocida).

Sirve para (a) validar el algoritmo con un BPM real exactamente conocido y
(b) generar un video de prueba reproducible sin necesitar a ninguna persona.

Modelo por canal k en {R, G, B}:

    C_k(t) = C0_k * (1 + alpha_k * s(t)) * (1 + leak_k * m(t)) + flicker(t) + ruido_k(t)

  s(t)      : pulso normalizado (suma de armónicos; la frecuencia varía con la
              respiración: arritmia sinusal respiratoria, RSA).
  alpha_k   : sensibilidad del canal al pulso (verde > rojo > azul, por la
              absorción de la hemoglobina).
  m(t)      : movimiento/cambio de iluminación, proceso Ornstein-Uhlenbeck
              (aleatorio, de baja frecuencia). Es MULTIPLICATIVO y casi común a
              los tres canales (leak_k ~ 1), por eso POS puede cancelarlo.
  flicker   : parpadeo de la luz. Se evalúa la senoide física en los instantes de
              muestreo, así que el ALIASING aparece solo.
  ruido_k   : ruido gaussiano del sensor.
Al final se cuantiza a 8 bits (0..255).
"""
from pathlib import Path

import cv2
import numpy as np


def _ou_process(n, dt, theta, std, rng):
    """Proceso de Ornstein-Uhlenbeck con desviación estándar estacionaria `std`."""
    sigma = std * np.sqrt(2.0 * theta)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = x[i - 1] - theta * x[i - 1] * dt + sigma * np.sqrt(dt) * rng.standard_normal()
    return x


def simulate_rgb(fs=30.0, duration=30.0, f0_mean=1.2, rsa_depth=0.08, f_resp=0.25,
                 n_harmonics=5, decay=1.2,
                 skin_rgb=(175.0, 120.0, 100.0), alphas=(0.008, 0.015, 0.006),
                 sensor_noise_std=1.0, motion_std=0.01, motion_theta=2.0,
                 flicker_hz=100.0, flicker_amp=1.0, quantize=True, seed=42):
    """
    Devuelve dict con: t, rgb (cuantizado), rgb_continuous (sin cuantizar), pulse,
    bpm_true_t (BPM instantáneo real), bpm_true_mean, fs, flicker_alias_hz.

    f0_mean = 1.2 Hz equivale a 72 BPM. flicker_hz=100 corresponde a una red de
    50 Hz (la luz parpadea al doble de la red); con fs=30 aparece en 10 Hz por aliasing.
    """
    rng = np.random.default_rng(seed)
    n = int(round(fs * duration))
    t = np.arange(n) / fs

    # Frecuencia cardíaca instantánea (con RSA) y su fase (integral de la frecuencia)
    f0_t = f0_mean + rsa_depth * np.sin(2 * np.pi * f_resp * t)
    phase = 2 * np.pi * np.cumsum(f0_t) / fs

    pulse = np.zeros(n)
    for k in range(1, n_harmonics + 1):
        pulse += (1.0 / k ** decay) * np.sin(k * phase + rng.uniform(0, 2 * np.pi))
    pulse /= np.max(np.abs(pulse))

    skin = np.asarray(skin_rgb, dtype=float)
    alphas = np.asarray(alphas, dtype=float)
    clean = skin * (1.0 + alphas * pulse[:, None])

    motion = _ou_process(n, 1.0 / fs, motion_theta, motion_std, rng)
    leak = np.array([1.0, 0.9, 1.1])          # el movimiento no afecta idéntico a cada canal
    moved = clean * (1.0 + motion[:, None] * leak)

    flicker = flicker_amp * np.sin(2 * np.pi * flicker_hz * t + rng.uniform(0, 2 * np.pi))
    noise = rng.normal(0.0, sensor_noise_std, size=(n, 3))
    continuous = moved + flicker[:, None] + noise
    rgb = np.clip(np.round(continuous), 0, 255) if quantize else continuous

    return {
        "t": t, "fs": float(fs), "rgb": rgb, "rgb_continuous": continuous,
        "rgb_clean": clean, "pulse": pulse, "motion": motion,
        "bpm_true_t": 60.0 * f0_t, "bpm_true_mean": float(60.0 * f0_t.mean()),
        "flicker_alias_hz": float(abs(flicker_hz - fs * round(flicker_hz / fs))),
    }


def write_synthetic_video(path, sim, size=(320, 240), pixel_noise_std=4.0, seed=0):
    """
    Renderiza la señal simulada como un video: cada fotograma es un parche de color
    (el color RGB simulado de ese instante) más ruido independiente por píxel.

    Devuelve la ROI central (x, y, w, h) para usar con manual_roi. No tiene rostro,
    así que el detector Haar no aplica: se usa ROI manual.
    """
    width, height = size
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"),
                             sim["fs"], (width, height))
    if not writer.isOpened():
        raise RuntimeError("No se pudo crear el video (códec MJPG no disponible).")
    rng = np.random.default_rng(seed)
    for color_rgb in sim["rgb_continuous"]:
        frame = color_rgb[None, None, :] + rng.normal(0, pixel_noise_std, (height, width, 3))
        frame = np.clip(np.round(frame), 0, 255).astype(np.uint8)
        writer.write(frame[:, :, ::-1])  # RGB -> BGR para OpenCV
    writer.release()
    return (width // 4, height // 4, width // 2, height // 2)
