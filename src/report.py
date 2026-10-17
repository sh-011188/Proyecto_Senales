"""
report.py - Interpretación automática de resultados y reporte en disco.

La entrega pide que cada gráfica tenga interpretación. Este módulo genera un
PRIMER BORRADOR de esa interpretación a partir de los números calculados
(niveles, deriva, pico espectral, armónicos, calidad, efecto del ruido).
Es un punto de partida: el grupo debe revisarlo y completarlo con lo que
observa en sus propias figuras.

  interpret(result)               -> dict {clave_figura: texto}
  save_report(result, out_dir)    -> resultados.json + reporte.md
"""
import json
from pathlib import Path

import numpy as np

from .config import BAND_HZ

TITULOS = {
    "01_roi": "1. Región de interés (ROI)",
    "02_rgb_crudo": "2. Representación temporal: series R, G, B",
    "03_preprocesado": "3. Primera etapa de procesamiento",
    "04_espectro_pos": "4. Análisis frecuencial (POS)",
    "05_espectro_verde": "5. Análisis frecuencial (canal verde)",
    "06_pulso_pos": "6. Señal de pulso recuperada",
    "07_ruido": "7. Ruido / degradación controlada",
}


def _confiabilidad(q):
    if q >= 0.5:
        return "alta"
    if q >= 0.3:
        return "media"
    return "baja"


def _harmonic_ratio(est):
    """Amplitud en 2*f0 relativa a la del pico f0 (pulso no senoidal -> armónicos)."""
    f, m = est["freqs"], est["magnitude"]
    f0 = est["peak_hz"]
    if 2 * f0 > f[-1]:
        return None
    a0 = m[np.argmin(np.abs(f - f0))]
    near = np.abs(f - 2 * f0) <= 0.1
    return float(m[near].max() / a0) if a0 > 0 and near.any() else None


def interpret(r):
    """Genera un texto de interpretación por figura + un resumen general."""
    fs, t, rgb = r["fs"], r["t"], r["rgb"]
    desc = r["descripcion_canales"]
    est_pos, est_g = r["est_pos"], r["est_green"]
    T = r["duration_s"]
    out = {}

    # 1. ROI
    cov = ", ".join(f"{100 * c:.0f} %" for c in r["cobertura_piel"])
    if r["roi_mode"] == "dedo":
        origen = "se configuró en modo «dedo sobre la cámara» (PPG por contacto con flash), analizando la región central del sensor sin detector de rostro"
        out["01_roi"] = (
            f"La ROI {origen}. En esta modalidad, la yema del dedo cubre el lente iluminada por el flash/linterna, "
            f"por lo que todo el tejido capilar refleja y modula la luz directamente con cada latido. "
            "Se promedian los píxeles de la zona central para maximizar la relación señal a ruido y evitar bordes."
        )
    else:
        origen = ("se definió manualmente" if r["roi_mode"] == "manual"
                  else f"se ubicó automáticamente en la zona «{r['roi_mode']}» a partir del rostro "
                       "detectado con el clasificador Haar (Viola-Jones)")
        out["01_roi"] = (
            f"La ROI {origen}. Se usan {len(r['roi'])} región(es) y la máscara de piel (espacio YCrCb) "
            f"conserva {cov} de los píxeles. Solo se promedian píxeles de piel: cabello, cejas y fondo no "
            "contienen pulso y agregarían ruido. Verifique en la figura que el recuadro verde cae sobre piel."
        )

    # 2. Señal cruda
    slope = {c: np.polyfit(t, rgb[:, i], 1)[0] * T for i, c in enumerate("RGB")}
    rel = {c: 100 * desc[c]["amplitud_pico_a_pico"] / desc[c]["media"] for c in "RGB"}
    out["02_rgb_crudo"] = (
        f"Señal discreta muestreada a fs = {fs:.2f} Hz (Ts = {1000 / fs:.1f} ms), N = {len(rgb)} muestras, "
        f"duración útil {T:.1f} s (se descartaron los primeros {r['discard_seconds']:.1f} s por la "
        f"auto-exposición). Niveles medios: R = {desc['R']['media']:.1f}, G = {desc['G']['media']:.1f}, "
        f"B = {desc['B']['media']:.1f} (escala 0-255). La variación pico a pico es pequeña respecto al nivel "
        f"medio (R {rel['R']:.1f} %, G {rel['G']:.1f} %, B {rel['B']:.1f} %): el pulso es una variación de "
        f"~1 % montada sobre una componente DC grande. Deriva lenta a lo largo del video: "
        f"R {slope['R']:+.2f}, G {slope['G']:+.2f}, B {slope['B']:+.2f} niveles (cambios de luz o movimiento). "
        "Los saltos bruscos, si aparecen, suelen ser movimientos o ajustes de exposición."
    )

    # 3. Preprocesado
    g_proc_std = 100 * np.std(rgb[:, 1] / rgb[:, 1].mean() - 1)
    out["03_preprocesado"] = (
        "Se normalizó el canal verde por su media (x/media − 1, es decir AC/DC) y se quitó la tendencia "
        f"lineal. La señal pasa de niveles absolutos (~{desc['G']['media']:.0f}) a variación relativa "
        f"centrada en cero (desviación ≈ {g_proc_std:.2f} %). Así los canales son comparables, se elimina la "
        f"componente DC (que dominaría el espectro en 0 Hz) y la deriva de {slope['G']:+.2f} niveles."
    )

    # 4. Espectro POS
    h = _harmonic_ratio(est_pos)
    harm = (f" En 2·f0 = {2 * est_pos['peak_hz']:.2f} Hz hay una componente de {100 * h:.0f} % de la "
            "amplitud del pico (armónico: el pulso es periódico pero no senoidal, serie de Fourier)."
            if h is not None and h > 0.15 else "")
    out["04_espectro_pos"] = (
        f"La FFT (ventana de Hann, zero-padding ×8) muestra el contenido en frecuencia de la señal POS. "
        f"Eje x: frecuencia en Hz (arriba en BPM = Hz × 60), de 0 a fs/2 = {fs / 2:.1f} Hz (Nyquist). "
        f"Dentro de la banda fisiológica {BAND_HZ[0]}-{BAND_HZ[1]} Hz el pico dominante está en "
        f"f0 = {est_pos['peak_hz']:.3f} Hz → {est_pos['bpm']:.1f} BPM. Calidad del pico "
        f"{est_pos['quality']:.2f} (confiabilidad {_confiabilidad(est_pos['quality'])}). "
        f"Resolución espectral real Δf = 1/T = {1 / T:.3f} Hz ≈ {60 / T:.1f} BPM: el zero-padding solo "
        f"interpola, no mejora este límite.{harm}"
    )

    # 5. Espectro verde
    diff = est_g["bpm"] - est_pos["bpm"]
    acuerdo = ("coinciden dentro de la resolución espectral, lo que da más confianza en la estimación"
               if abs(diff) <= 60 / T + 1 else
               "NO coinciden: al menos uno de los métodos está siguiendo ruido (movimiento, luz)")
    out["05_espectro_verde"] = (
        f"Con solo el canal verde (método base) el pico está en {est_g['peak_hz']:.3f} Hz → "
        f"{est_g['bpm']:.1f} BPM (calidad {est_g['quality']:.2f}). Diferencia con POS: {diff:+.1f} BPM; "
        f"los dos métodos {acuerdo}. El verde es el canal más sensible a la hemoglobina; POS combina "
        "R, G y B para cancelar las variaciones de brillo comunes a los tres canales."
    )

    # 6. Pulso
    t0 = 1 / est_pos["peak_hz"]
    out["06_pulso_pos"] = (
        f"Forma de onda de la señal de pulso extraída con POS. Las líneas rojas marcan el periodo estimado "
        f"T0 = 1/f0 = {t0:.2f} s; en 10 s caben ≈ {10 / t0:.0f} ciclos. Si las oscilaciones siguen las líneas, "
        "la señal es casi periódica y el pico espectral corresponde a los latidos. Variaciones de amplitud o "
        "ciclos irregulares indican ruido residual o variación natural del ritmo (respiración)."
    )

    # 7. Ruido
    nz = r["ruido"]
    cambio = nz["bpm_con_ruido"] - nz["bpm_original"]
    out["07_ruido"] = (
        f"Se sumó ruido blanco gaussiano a la señal G normalizada con SNR = {nz['snr_db']:.0f} dB "
        f"(σ = {nz['sigma']:.2e}, semilla {nz['semilla']}). En el tiempo la forma del pulso se vuelve "
        f"difícil de ver; en frecuencia el ruido blanco se reparte en todas las frecuencias y levanta el "
        f"piso del espectro. El pico pasa de {nz['bpm_original']:.1f} a {nz['bpm_con_ruido']:.1f} BPM "
        f"({cambio:+.1f}) y la calidad de {nz['calidad_original']:.2f} a {nz['calidad_con_ruido']:.2f}. "
        "Ruidos reales que afectan la señal: ruido del sensor y de cuantización (8 bits), compresión del "
        "video, movimiento de la cabeza, cambios y parpadeo de la iluminación (aliasing si la luz parpadea "
        "por encima de fs/2)."
    )

    # Resumen
    resumen = (f"BPM estimado (POS): {est_pos['bpm']:.1f} ± {60 / T / 2:.1f} BPM, confiabilidad "
               f"{_confiabilidad(est_pos['quality'])}. Canal verde: {est_g['bpm']:.1f} BPM.")
    if r.get("expected_bpm") is not None:
        resumen += (f" Referencia manual {r['expected_bpm']:.1f} BPM → error POS {r['error_pos']:+.1f}, "
                    f"verde {r['error_verde']:+.1f} BPM.")
    out["resumen"] = resumen
    return out


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def summary_dict(r):
    """Subconjunto serializable del resultado (sin arreglos grandes)."""
    keys = ["video", "roi_mode", "face_box", "roi", "cobertura_piel", "use_bandpass", "discard_seconds",
            "info", "fs", "duration_s", "descripcion_canales", "bpm_pos", "quality_pos", "bpm_verde",
            "quality_verde", "resolucion_bpm", "expected_bpm", "error_pos", "error_verde", "ruido",
            "warnings", "figuras", "interpretaciones"]
    d = {k: r[k] for k in keys if k in r}
    d["peak_hz_pos"] = r["est_pos"]["peak_hz"]
    d["peak_hz_verde"] = r["est_green"]["peak_hz"]
    return _to_jsonable(d)


def save_report(r, out_dir, prefix=""):
    """Guarda resultados.json y reporte.md (listo para copiar al README)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = summary_dict(r)
    (out / f"{prefix}resultados.json").write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    info, it = r["info"], r["interpretaciones"]
    lines = [
        f"# Reporte rPPG - {Path(r['video']).name}",
        "",
        "> Uso educativo. No es una medición clínica ni diagnóstica.",
        "",
        f"**Resumen:** {it['resumen']}",
        "",
        "## Adquisición",
        "",
        "| Parámetro | Valor |",
        "|---|---|",
        f"| fs = FPS | {info['fps']:.3f} Hz |",
        f"| Ts = 1/fs | {1000 * info['Ts_s']:.2f} ms |",
        f"| Resolución | {info['width']} × {info['height']} px |",
        f"| Fotogramas | {info['n_frames_nominal']} |",
        f"| Duración total / útil | {info['duration_s']:.1f} s / {r['duration_s']:.1f} s |",
        f"| Nyquist fs/2 | {info['fps'] / 2:.2f} Hz |",
        f"| Resolución espectral 1/T | {60 / r['duration_s']:.2f} BPM |",
        "",
        "## Caracterización de las series R, G, B (niveles 0-255)",
        "",
        "| Canal | N | mín | máx | pico a pico | media | desv. est. |",
        "|---|---|---|---|---|---|---|",
    ]
    for c, d in r["descripcion_canales"].items():
        lines.append(f"| {c} | {d['n_muestras']} | {d['minimo']:.2f} | {d['maximo']:.2f} | "
                     f"{d['amplitud_pico_a_pico']:.2f} | {d['media']:.2f} | {d['desv_estandar']:.3f} |")
    lines.append("")
    for key, title in TITULOS.items():
        lines += [f"## {title}", ""]
        if key in r.get("figuras", {}):
            lines += [f"![{title}]({r['figuras'][key]})", ""]
        lines += [it[key], ""]
    if r["warnings"]:
        lines += ["## Avisos", ""] + [f"- {w}" for w in r["warnings"]] + [""]
    (out / f"{prefix}reporte.md").write_text("\n".join(lines), encoding="utf-8")
