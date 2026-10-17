"""
video_io.py - Lectura de video y metadatos de muestreo.

Concepto de Teoría de Señales: un video es una señal MUESTREADA en el tiempo.
Su frecuencia de muestreo es fs = FPS (fotogramas por segundo) y su periodo
de muestreo es Ts = 1/fs.
"""
from pathlib import Path

import cv2
import numpy as np


def _open(video_path):
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el video: {path}")
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV no pudo abrir el video: {path}")
    return cap


def get_video_info(video_path):
    """Devuelve FPS (= fs), Ts, tamaño y duración nominal del video."""
    cap = _open(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("El video no reporta FPS válidos; no se puede definir fs.")
    return {
        "fps": fps,
        "Ts_s": 1.0 / fps,
        "n_frames_nominal": n_frames,
        "width": width,
        "height": height,
        "duration_s": n_frames / fps,
    }


def read_first_frames(video_path, n=30):
    """Lee los primeros n fotogramas (BGR). Se usan para detectar el rostro."""
    cap = _open(video_path)
    frames = []
    while len(frames) < n:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        raise ValueError("No se pudo leer ningún fotograma del video.")
    return frames


def iter_frames(video_path, max_seconds=None):
    """
    Generador de fotogramas (índice, imagen BGR).
    Se lee uno a uno (streaming) para no cargar todo el video en memoria.
    """
    cap = _open(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    max_frames = int(max_seconds * fps) if max_seconds else None
    idx = 0
    try:
        while True:
            if max_frames is not None and idx >= max_frames:
                break
            ok, frame = cap.read()
            if not ok:
                break
            yield idx, frame
            idx += 1
    finally:
        cap.release()
