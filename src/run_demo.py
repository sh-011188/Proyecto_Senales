"""
run_demo.py - Demostración desde la terminal (desde la raíz del repositorio).

  python -m src.run_demo --simulado
  python -m src.run_demo --video data/mi_video.mp4 --esperado 72
  python -m src.run_demo --video data/mi_video.mp4 --roi-mode mejillas
  python -m src.run_demo --video data/mi_video.mp4 --roi 120 40 100 40
"""
import argparse

from .pipeline import analyze_video, evaluate_on_simulation
from .simulation import simulate_rgb, write_synthetic_video


def main():
    p = argparse.ArgumentParser(description="Estimación de BPM por rPPG (uso educativo).")
    p.add_argument("--video", help="Ruta del video con un rostro de frente.")
    p.add_argument("--simulado", action="store_true",
                   help="Evalúa con una señal sintética y con un video sintético (verdad conocida).")
    p.add_argument("--roi-mode", default="frente", choices=["frente", "mejillas", "rostro", "dedo"],
                   help="Zona de análisis: frente, mejillas, rostro o dedo (PPG por contacto con flash).")
    p.add_argument("--roi", nargs=4, type=int, metavar=("X", "Y", "W", "H"),
                   help="ROI manual en píxeles (evita el detector de rostro).")
    p.add_argument("--esperado", type=float, help="BPM de referencia medido a mano (opcional).")
    p.add_argument("--out", default="results", help="Carpeta de salida para las figuras.")
    args = p.parse_args()

    if args.simulado:
        evaluate_on_simulation(out_dir=args.out)
        sim = simulate_rgb()
        roi = write_synthetic_video("data/generated/sim.avi", sim)
        print("\nVideo sintético generado: data/generated/sim.avi (ROI manual central)")
        analyze_video("data/generated/sim.avi", manual_roi=roi,
                      expected_bpm=sim["bpm_true_mean"], out_dir=args.out, prefix="simvideo_")
    elif args.video:
        analyze_video(args.video, roi_mode=args.roi_mode, manual_roi=args.roi,
                      expected_bpm=args.esperado, out_dir=args.out)
    else:
        p.error("Indica --video RUTA o --simulado.")


if __name__ == "__main__":
    main()
