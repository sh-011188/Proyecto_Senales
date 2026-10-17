# Datos

## Video propio (principal)
Coloca aquí un video corto (idealmente 20-30 s, unos pocos MB) como `data/mi_video.mp4`.

Cómo grabarlo: celular apoyado, rostro de frente y completo, sin hablar ni moverse, luz estable (sin parpadeo), buena resolución (720p o más) y 30 fps.

Documenta en el README principal: dispositivo, FPS, resolución, duración, condiciones de luz y tu pulso medido a mano (BPM de referencia).

**Privacidad:** sube únicamente videos tuyos o de personas que dieron su consentimiento. Si el repositorio es público, considera subir solo una muestra recortada o no subir el video y dejar instrucciones.

## Datos sintéticos (no se suben)
`python -m src.run_demo --simulado` genera `data/generated/sim.avi` (ignorado por git) y las figuras en `results/`. La señal se genera con `src/simulation.py` y una semilla fija, así que es reproducible.
