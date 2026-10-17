"""
pipeline.py - Une todos los módulos en dos funciones de alto nivel:

  analyze_video(...)        : video real (o sintético) -> BPM estimado.
  evaluate_on_simulation()  : señal simulada -> BPM estimado vs. BPM real conocido.

USO EDUCATIVO: la estimación no es un dato clínico ni diagnóstico.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from . import plots, report
from .analysis import compute_spectrum, describe_signal, estimate_bpm_from_spectrum
from .bpm import estimate_bpm, green_channel_signal
from .config import (DISCARD_SECONDS, FACE_DETECT_FRAMES, MIN_DURATION_SECONDS, NOISE_SEED,
                     NOISE_SNR_DB)
from .preprocessing import add_white_noise, discard_start
from .roi import build_skin_masks, estimate_face_box, rois_from_face_box, validate_manual_roi
from .signal_extraction import extract_rgb_series
from .simulation import simulate_rgb
from .video_io import get_video_info, read_first_frames


def _save_path(out_dir, name):
    return str(Path(out_dir) / name) if out_dir else None


def analyze_video(video_path, roi_mode="frente", manual_roi=None, max_seconds=None,
                  discard_seconds=DISCARD_SECONDS, expected_bpm=None, out_dir=None,
                  show=False, prefix="", use_skin_mask=True, use_bandpass=False,
                  noise_snr_db=NOISE_SNR_DB, save_report=True, progress=None):
    """
    Pasos: info del video (fs) -> ROI -> serie RGB -> descartar inicio ->
    caracterización -> POS + FFT -> BPM. Guarda figuras en out_dir si se indica.
    expected_bpm: pulso de referencia medido a mano (opcional) para calcular el error.
    use_bandpass: aplica el filtro Butterworth pasa banda antes de la FFT (entrega final).
    noise_snr_db: SNR del experimento de ruido controlado.
    save_report: si hay out_dir, guarda también resultados.json y reporte.md.
    progress: función opcional progress(fraccion, mensaje) para mostrar avance (web).
    """
    def _p(frac, msg):
        if progress:
            progress(frac, msg)

    _p(0.02, "Leyendo metadatos del video (fs, Ts)")
    info = get_video_info(video_path)
    fs = info["fps"]

    _p(0.06, "Detectando el rostro y definiendo la ROI")
    frames = read_first_frames(video_path, FACE_DETECT_FRAMES)
    if manual_roi is not None:
        rois, face_box = validate_manual_roi(manual_roi, frames[0].shape), None
    elif roi_mode == "dedo":
        # Video de dedo sobre la cámara (con flash): toma la zona central directamente sin detector de rostro
        h, w = frames[0].shape[:2]
        rois, face_box = [(int(0.15 * w), int(0.15 * h), int(0.70 * w), int(0.70 * h))], None
        use_skin_mask = False
    else:
        face_box = estimate_face_box(frames)
        rois = rois_from_face_box(face_box, roi_mode, frames[0].shape)
    masks, warnings, coverages = (build_skin_masks(frames[0], rois) if use_skin_mask
                                  else ([None] * len(rois), [], [1.0] * len(rois)))
    plots.plot_frame_with_roi(frames[0], rois, face_box, masks, _save_path(out_dir, f"{prefix}01_roi.png"))

    _p(0.12, "Extrayendo las series R, G, B fotograma a fotograma")
    data = extract_rgb_series(video_path, rois, masks=masks, max_seconds=max_seconds,
                              progress=(lambda f: _p(0.12 + 0.6 * f, "Extrayendo las series R, G, B")))
    _p(0.75, "Procesando la señal y calculando el espectro")
    t, rgb = discard_start(data["t"], data["rgb"], fs, discard_seconds)
    duration = len(rgb) / fs
    if duration < MIN_DURATION_SECONDS:
        warnings.append(f"Duración útil {duration:.1f} s < {MIN_DURATION_SECONDS:.0f} s: "
                        "la resolución en BPM será baja.")

    plots.plot_rgb_time(t, rgb, save_path=_save_path(out_dir, f"{prefix}02_rgb_crudo.png"))
    g_proc = green_channel_signal(rgb)
    plots.plot_raw_vs_processed(t, rgb[:, 1], g_proc,
                                save_path=_save_path(out_dir, f"{prefix}03_preprocesado.png"))

    est_pos = estimate_bpm(rgb, fs, "pos", use_bandpass=use_bandpass)
    est_green = estimate_bpm(rgb, fs, "green", use_bandpass=use_bandpass)
    plots.plot_spectrum(est_pos["freqs"], est_pos["magnitude"], est_pos,
                        title="Espectro de la señal de pulso (método POS)",
                        true_bpm=expected_bpm, save_path=_save_path(out_dir, f"{prefix}04_espectro_pos.png"))
    plots.plot_spectrum(est_green["freqs"], est_green["magnitude"], est_green,
                        title="Espectro del canal verde (método base)",
                        true_bpm=expected_bpm, save_path=_save_path(out_dir, f"{prefix}05_espectro_verde.png"))
    plots.plot_pulse_signal(t, est_pos["pulse"], est_pos,
                            save_path=_save_path(out_dir, f"{prefix}06_pulso_pos.png"))

    # Ruido controlado (requisito 4.5): G normalizado + ruido blanco con SNR conocida.
    _p(0.88, "Experimento de ruido controlado")
    g_noisy, noise_sigma = add_white_noise(g_proc, noise_snr_db, seed=NOISE_SEED)
    f_c, m_c = compute_spectrum(g_proc, fs)
    f_n, m_n = compute_spectrum(g_noisy, fs)
    est_clean = estimate_bpm_from_spectrum(f_c, m_c)
    est_noisy = estimate_bpm_from_spectrum(f_n, m_n)
    plots.plot_noise_comparison(t, g_proc, g_noisy, f_c, m_c, m_n, est_clean, est_noisy, noise_snr_db,
                                save_path=_save_path(out_dir, f"{prefix}07_ruido.png"))

    names = ["01_roi", "02_rgb_crudo", "03_preprocesado", "04_espectro_pos",
             "05_espectro_verde", "06_pulso_pos", "07_ruido"]
    result = {
        "video": str(video_path), "roi_mode": roi_mode if manual_roi is None else "manual",
        "face_box": face_box, "use_bandpass": use_bandpass, "discard_seconds": discard_seconds,
        "expected_bpm": expected_bpm,
        "ruido": {"snr_db": noise_snr_db, "sigma": noise_sigma, "semilla": NOISE_SEED,
                  "bpm_original": est_clean["bpm"], "bpm_con_ruido": est_noisy["bpm"],
                  "calidad_original": est_clean["quality"], "calidad_con_ruido": est_noisy["quality"]},
        "figuras": {n: f"{prefix}{n}.png" for n in names} if out_dir else {},
        "info": info, "fs": fs, "roi": rois, "cobertura_piel": coverages, "duration_s": duration,
        "descripcion_canales": {n: describe_signal(rgb[:, i], fs) for i, n in enumerate("RGB")},
        "bpm_pos": est_pos["bpm"], "quality_pos": est_pos["quality"],
        "bpm_verde": est_green["bpm"], "quality_verde": est_green["quality"],
        "resolucion_bpm": est_pos["resolucion_bpm"], "warnings": warnings,
        "t": t, "rgb": rgb, "est_pos": est_pos, "est_green": est_green,
    }
    if expected_bpm is not None:
        result["error_pos"] = est_pos["bpm"] - expected_bpm
        result["error_verde"] = est_green["bpm"] - expected_bpm
    result["interpretaciones"] = report.interpret(result)
    if out_dir and save_report:
        report.save_report(result, out_dir, prefix)
    _print_summary(result, expected_bpm)
    _p(1.0, "Listo")
    if show:
        plt.show()
    else:
        plt.close("all")
    return result


def evaluate_on_simulation(out_dir=None, show=False, **sim_kwargs):
    """Simula, estima con POS y con canal verde, y compara con el BPM real conocido."""
    sim = simulate_rgb(**sim_kwargs)
    fs, rgb = sim["fs"], sim["rgb"]
    est_pos = estimate_bpm(rgb, fs, "pos")
    est_green = estimate_bpm(rgb, fs, "green")
    truth = sim["bpm_true_mean"]
    plots.plot_simulation_overview(sim, _save_path(out_dir, "sim_01_pulso_y_verdad.png"))
    plots.plot_rgb_time(sim["t"], rgb, "Series RGB simuladas (con ruido, movimiento y cuantización)",
                        _save_path(out_dir, "sim_02_rgb.png"))
    plots.plot_spectrum(est_pos["freqs"], est_pos["magnitude"], est_pos,
                        title="Simulación: espectro (POS)", true_bpm=truth,
                        save_path=_save_path(out_dir, "sim_03_espectro_pos.png"))
    out = {"sim": sim, "truth_bpm": truth, "est_pos": est_pos, "est_green": est_green,
           "error_pos": est_pos["bpm"] - truth, "error_verde": est_green["bpm"] - truth}
    print(f"BPM real (media): {truth:.2f} | POS: {est_pos['bpm']:.2f} (error {out['error_pos']:+.2f}) "
          f"| verde: {est_green['bpm']:.2f} (error {out['error_verde']:+.2f}) "
          f"| resolución espectral: ±{est_pos['resolucion_bpm']/2:.1f} BPM")
    if show:
        plt.show()
    else:
        plt.close("all")
    return out


def _print_summary(r, expected_bpm):
    print("=" * 60)
    print(f"fs = {r['fs']:.3f} Hz (Ts = {1/r['fs']*1000:.2f} ms) | duración útil = {r['duration_s']:.1f} s")
    print(f"Resolución espectral real ≈ {r['resolucion_bpm']:.1f} BPM (1/T)")
    print(f"BPM estimado (POS):   {r['bpm_pos']:.1f}  | calidad {r['quality_pos']:.2f}")
    print(f"BPM estimado (verde): {r['bpm_verde']:.1f}  | calidad {r['quality_verde']:.2f}")
    if expected_bpm is not None:
        print(f"Referencia manual: {expected_bpm:.1f} -> error POS {r['error_pos']:+.1f} | verde {r['error_verde']:+.1f}")
    for w in r["warnings"]:
        print("AVISO:", w)
    print("Uso educativo: no es una medición clínica ni diagnóstica.")
    print("=" * 60)
