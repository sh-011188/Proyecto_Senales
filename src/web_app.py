"""
web_app.py - Interfaz web local: subir un video y ver los resultados.

Uso (desde la raíz del repositorio):

    python -m src.web_app            # abre http://127.0.0.1:5000

Flujo: el navegador sube el video -> se guarda en data/uploads/ -> se ejecuta
pipeline.analyze_video en un hilo -> las figuras, resultados.json y reporte.md
quedan en results/web/<fecha>_<nombre>/ -> la página muestra BPM, tablas,
figuras e interpretaciones.

Todo corre en el computador local: el video NO se envía a ningún servidor externo.
"""
import argparse
import re
import shutil
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventanas: las figuras solo se guardan como PNG

from flask import Flask, abort, jsonify, request, send_file, send_from_directory  # noqa: E402

from .config import NOISE_SNR_DB  # noqa: E402
from .pipeline import analyze_video  # noqa: E402
from .report import TITULOS, summary_dict  # noqa: E402
from .simulation import simulate_rgb, write_synthetic_video  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "uploads"
RESULTS_DIR = ROOT / "results" / "web"
WEB_DIR = Path(__file__).resolve().parent / "web"
ALLOWED_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp"}

app = Flask(__name__, static_folder=str(WEB_DIR / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

JOBS = {}                         # job_id -> estado
_ANALYSIS_LOCK = threading.Lock()  # matplotlib no es seguro con varios hilos a la vez


def _safe_name(name):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(name).stem).strip("_") or "video"
    return stem[:40]


def _run_job(job_id, video_path, out_dir, **kwargs):
    job = JOBS[job_id]

    def progress(frac, msg):
        job["progreso"], job["mensaje"] = float(frac), msg

    try:
        with _ANALYSIS_LOCK:
            job["estado"] = "procesando"
            r = analyze_video(str(video_path), out_dir=str(out_dir), progress=progress, **kwargs)
        data = summary_dict(r)
        data["titulos"] = TITULOS
        data["carpeta"] = str(out_dir.relative_to(ROOT))
        job.update(estado="listo", progreso=1.0, mensaje="Listo", resultado=data)
    except Exception as e:  # se muestra en la página
        job.update(estado="error", error=str(e))


def _start_job(video_path, display_name, **kwargs):
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + _safe_name(display_name) + "_" + uuid.uuid4().hex[:4]
    out_dir = RESULTS_DIR / job_id
    JOBS[job_id] = {"estado": "en_cola", "progreso": 0.0, "mensaje": "En cola", "nombre": display_name}
    threading.Thread(target=_run_job, args=(job_id, video_path, out_dir), kwargs=kwargs, daemon=True).start()
    return job_id


def _float_or_none(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.post("/api/analizar")
def api_analizar():
    f = request.files.get("video")
    if f is None or not f.filename:
        return jsonify(error="No se recibió ningún video."), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error=f"Formato {ext} no soportado. Use: {', '.join(sorted(ALLOWED_EXT))}"), 400
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe_name(f.filename)}{ext}"
    f.save(path)

    roi_mode = request.form.get("roi_mode", "frente")
    if roi_mode not in ("frente", "mejillas", "rostro", "dedo"):
        roi_mode = "frente"
    snr = _float_or_none(request.form.get("snr_db"))
    job_id = _start_job(path, f.filename, roi_mode=roi_mode,
                        expected_bpm=_float_or_none(request.form.get("esperado")),
                        use_bandpass=request.form.get("bandpass") == "1",
                        noise_snr_db=NOISE_SNR_DB if snr is None else snr)
    return jsonify(job_id=job_id)


@app.post("/api/demo")
def api_demo():
    """Genera un video sintético con BPM conocido y lo analiza (sin cámara)."""
    sim = simulate_rgb()
    path = ROOT / "data" / "generated" / "sim.avi"
    roi = write_synthetic_video(str(path), sim)
    snr = _float_or_none(request.form.get("snr_db"))
    job_id = _start_job(path, "video_sintetico.avi", manual_roi=roi,
                        expected_bpm=float(sim["bpm_true_mean"]),
                        use_bandpass=request.form.get("bandpass") == "1",
                        noise_snr_db=NOISE_SNR_DB if snr is None else snr)
    return jsonify(job_id=job_id)


@app.get("/api/estado/<job_id>")
def api_estado(job_id):
    job = JOBS.get(job_id)
    if job is None:
        return jsonify(error="Trabajo no encontrado."), 404
    return jsonify(job)


@app.get("/resultados/<job_id>/<path:filename>")
def resultados(job_id, filename):
    folder = RESULTS_DIR / job_id
    if not folder.is_dir():
        abort(404)
    return send_from_directory(folder, filename)


@app.get("/api/descargar/<job_id>")
def descargar(job_id):
    folder = RESULTS_DIR / job_id
    if not folder.is_dir():
        abort(404)
    zip_path = shutil.make_archive(str(RESULTS_DIR / f"_{job_id}"), "zip", folder)
    return send_file(zip_path, as_attachment=True, download_name=f"rppg_{job_id}.zip")


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="El video supera 500 MB. Recórtelo a 20-30 s."), 413


def main():
    p = argparse.ArgumentParser(description="Interfaz web local para rPPG.")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--no-browser", action="store_true", help="No abrir el navegador automáticamente.")
    args = p.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    print(f"Abriendo {url}  (Ctrl+C para salir)")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
