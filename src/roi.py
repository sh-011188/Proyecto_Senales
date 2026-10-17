"""
roi.py - Detección del rostro y definición de la región de interés (ROI).

Se usa el detector de rostros en cascada de Haar (Viola & Jones, 2001) que
viene incluido en OpenCV: no requiere descargas ni librerías extra.

Decisión de diseño: el rostro se detecta en los primeros fotogramas y se toma
la MEDIANA de las cajas encontradas. La ROI queda FIJA durante todo el video.
Es simple y estable, pero asume que la persona permanece quieta (limitación
que se documenta en el README).
"""
import cv2
import numpy as np

from .config import ROI_FRACTIONS


def _load_cascade():
    if not hasattr(cv2, "CascadeClassifier"):
        raise RuntimeError(
            f"Esta versión de OpenCV ({cv2.__version__}) no incluye el detector Haar. "
            "Instale opencv-python-headless<5 (pip install -r requirements.txt) o use una ROI manual."
        )
    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        raise RuntimeError(f"No se pudo cargar el clasificador Haar: {path}")
    return cascade


def detect_face_box(frame_bgr, cascade=None):
    """Devuelve (x, y, w, h) del rostro más grande, o None si no hay."""
    cascade = cascade or _load_cascade()
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)  # mejora contraste para el detector
    min_side = int(0.15 * min(gray.shape))
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side)
    )
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
    return int(x), int(y), int(w), int(h)


def estimate_face_box(frames):
    """Mediana de las detecciones en varios fotogramas (más estable que una sola)."""
    cascade = _load_cascade()
    boxes = [b for b in (detect_face_box(f, cascade) for f in frames) if b is not None]
    if len(boxes) < max(3, len(frames) // 5):
        raise RuntimeError(
            "No se detectó un rostro frontal de forma consistente. "
            "Revisa que el rostro se vea de frente, bien iluminado y sin girar el video, "
            "o define la ROI a mano con manual_roi=(x, y, w, h)."
        )
    return tuple(int(v) for v in np.median(np.array(boxes), axis=0))


def rois_from_face_box(face_box, mode, frame_shape):
    """Convierte la caja del rostro en una lista de rectángulos ROI (x, y, w, h)."""
    if mode not in ROI_FRACTIONS:
        raise ValueError(f"Modo de ROI inválido: {mode}. Opciones: {list(ROI_FRACTIONS)}")
    fx, fy, fw, fh = face_box
    height, width = frame_shape[:2]
    rois = []
    for rx, ry, rw, rh in ROI_FRACTIONS[mode]:
        x = max(0, int(fx + rx * fw))
        y = max(0, int(fy + ry * fh))
        w = int(rw * fw)
        h = int(rh * fh)
        w = min(w, width - x)
        h = min(h, height - y)
        if w < 4 or h < 4:
            raise RuntimeError("La ROI quedó demasiado pequeña o fuera del cuadro.")
        rois.append((x, y, w, h))
    return rois


def validate_manual_roi(manual_roi, frame_shape):
    """Valida una ROI definida a mano (x, y, w, h) contra el tamaño del cuadro."""
    x, y, w, h = [int(v) for v in manual_roi]
    height, width = frame_shape[:2]
    if x < 0 or y < 0 or w < 4 or h < 4 or x + w > width or y + h > height:
        raise ValueError(
            f"ROI manual {manual_roi} fuera del cuadro de {width}x{height} píxeles."
        )
    return [(x, y, w, h)]


def build_skin_masks(frame_bgr, rois, min_coverage=0.2):
    """
    Máscara de piel por ROI, calculada UNA vez sobre un fotograma de referencia.

    Se convierte a YCrCb y se conservan los píxeles con crominancia típica de piel
    (Cr en [133, 173], Cb en [77, 127]; umbrales clásicos de Chai & Ngan, 1999).
    Sirve para excluir cabello, cejas, sombras u objetos que caigan dentro del
    rectángulo y que "diluirían" la señal del pulso.

    Si una ROI conserva menos de `min_coverage` de sus píxeles, se descarta la
    máscara de esa ROI (se usa el rectángulo completo) y se avisa.
    Devuelve (lista de máscaras uint8 o None, lista de avisos, lista de coberturas).
    """
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    masks, warnings, coverages = [], [], []
    for (x, y, w, h) in rois:
        crop = ycrcb[y:y + h, x:x + w]
        mask = cv2.inRange(crop, (0, 133, 77), (255, 173, 127))  # (Y, Cr, Cb)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        coverage = float(np.count_nonzero(mask)) / mask.size
        coverages.append(coverage)
        if coverage < min_coverage:
            masks.append(None)
            warnings.append(
                f"ROI {(x, y, w, h)}: solo {coverage:.0%} de píxeles de piel; "
                "se usa el rectángulo completo (revisa la figura de la ROI)."
            )
        else:
            masks.append(mask)
    return masks, warnings, coverages
