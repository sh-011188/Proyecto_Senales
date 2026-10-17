"""
signal_extraction.py - De video a series temporales.

Idea central: por cada fotograma k se promedia el color (R, G, B) de los píxeles
de piel dentro de la ROI. El resultado es una señal discreta de 3 canales:

    R[k], G[k], B[k]      con      t_k = k * Ts = k / fs

Promediar muchos píxeles reduce el ruido (el ruido independiente baja como
1/sqrt(N)) y, además, "recupera" variaciones menores a 1 nivel de 8 bits que un
solo píxel no podría representar.
"""
import cv2
import numpy as np

from .video_io import get_video_info, iter_frames


def extract_rgb_series(video_path, rois, masks=None, max_seconds=None, progress=None):
    """
    Promedia R, G, B dentro de cada ROI (solo píxeles de la máscara, si hay) y
    combina las ROI ponderando por su número de píxeles.

    Devuelve dict con:
        rgb : array (N, 3) en orden R, G, B
        t   : array (N,) tiempos en segundos
        fs  : frecuencia de muestreo (= FPS del video)
    """
    info = get_video_info(video_path)
    fps = info["fps"]
    masks = masks if masks is not None else [None] * len(rois)
    weights = np.array(
        [float(np.count_nonzero(m)) if m is not None else float(w * h)
         for m, (_, _, w, h) in zip(masks, rois)]
    )

    n_total = max(1, info["n_frames_nominal"])
    samples = []
    for idx, frame in iter_frames(video_path, max_seconds=max_seconds):
        means = []
        for (x, y, w, h), mask in zip(rois, masks):
            b, g, r, _ = cv2.mean(frame[y:y + h, x:x + w], mask=mask)  # OpenCV: BGR
            means.append((r, g, b))
        samples.append(np.average(means, axis=0, weights=weights))
        if progress and idx % 15 == 0:
            progress(min(1.0, idx / n_total))

    if not samples:
        raise ValueError("No se extrajo ningún fotograma.")
    rgb = np.asarray(samples, dtype=float)
    t = np.arange(len(rgb)) / fps
    return {"rgb": rgb, "t": t, "fs": fps}
