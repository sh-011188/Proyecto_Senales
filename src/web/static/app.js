// app.js - Lógica de la interfaz: subir video, consultar el progreso y mostrar resultados.
(() => {
  const $ = (id) => document.getElementById(id);
  let file = null;
  let roiMode = "frente";
  let pollTimer = null;

  // ---------- Selección del video ----------
  const dz = $("dropzone");
  const input = $("video-input");

  // ---------- Opciones ----------
  const ROI_HINTS = {
    frente: "💡 <b>Frente:</b> Detección automática de rostro (Haar) y piel YCrCb. Excelente perfusión capilar sin contacto.",
    mejillas: "💡 <b>Mejillas:</b> Dos regiones en los pómulos. Ideal si tienes flequillo o cabello sobre la frente.",
    rostro: "💡 <b>Rostro:</b> Región amplia que cubre todo el óvalo facial.",
    dedo: "💡 <b>Dedo con linterna:</b> Apoya la yema del dedo sobre la cámara del celular con la linterna encendida. ¡No requiere rostro y la señal de pulso es muy directa!"
  };

  function selectRoi(mode, customHint = null) {
    roiMode = mode;
    document.querySelectorAll("#roi-group .seg").forEach((x) => {
      if (x.dataset.value === mode) x.classList.add("active");
      else x.classList.remove("active");
    });
    $("roi-hint").innerHTML = customHint || ROI_HINTS[roiMode] || "";
  }

  function setFile(f) {
    if (!f) return;
    file = f;
    const prev = $("video-preview");
    prev.src = URL.createObjectURL(f);
    prev.hidden = false;
    prev.play().catch(() => {});
    $("dz-content").hidden = true;
    dz.querySelector(".dz-file")?.remove();

    // Auto-detectar por nombre de archivo
    if (/(dedo|finger|linterna|flash|contacto|contact|ppg)/i.test(f.name)) {
      selectRoi("dedo", "✨ <b>Detectado por nombre:</b> Video de dedo / linterna. Opción seleccionada automáticamente.");
    }

    const tag = document.createElement("div");
    tag.className = "dz-file";
    tag.innerHTML = `<span>🎬 ${f.name}</span><span>${(f.size / 1e6).toFixed(1)} MB · clic para cambiar</span>`;
    dz.appendChild(tag);
    $("btn-analizar").disabled = false;

    // Auto-detectar analizando el primer fotograma en un canvas rápido
    prev.onloadeddata = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = 40;
        canvas.height = 40;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(prev, 0, 0, 40, 40);
        const data = ctx.getImageData(0, 0, 40, 40).data;
        let rSum = 0, gSum = 0, bSum = 0;
        for (let i = 0; i < data.length; i += 4) {
          rSum += data[i];
          gSum += data[i + 1];
          bSum += data[i + 2];
        }
        const n = data.length / 4;
        const avgR = rSum / n;
        const avgG = gSum / n;
        const avgB = bSum / n;
        // Predominio de rojo típico de dedo iluminado con linterna
        if (avgR > 40 && (avgR > avgB * 1.15 || (avgR > 50 && avgB < 25))) {
          selectRoi("dedo", "✨ <b>Detectado automáticamente:</b> Video de dedo / linterna (PPG por contacto). Opción activada.");
        }
      } catch (_) {}
    };
  }

  input.addEventListener("change", (e) => setFile(e.target.files[0]));
  ["dragenter", "dragover"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
  dz.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

  document.querySelectorAll("#roi-group .seg").forEach((b) =>
    b.addEventListener("click", () => selectRoi(b.dataset.value)));
  const updateSnrBadge = (val) => {
    $("snr-val").textContent = val;
    const v = Number(val);
    let txt = "";
    if (v >= 15) txt = `${v} dB: Señal muy limpia (poco ruido)`;
    else if (v > 0) txt = `${v} dB: Ruido leve / moderado`;
    else if (v === 0) txt = "0 dB: Señal = Ruido (potencia igualada)";
    else if (v >= -5) txt = `${v} dB: Ruido dominante (más ruido que pulso)`;
    else txt = `${v} dB: Prueba extrema (10× más ruido que pulso)`;
    const badge = $("snr-badge");
    if (badge) badge.textContent = txt;
  };
  $("snr").addEventListener("input", (e) => updateSnrBadge(e.target.value));

  function commonForm() {
    const fd = new FormData();
    fd.append("snr_db", $("snr").value);
    fd.append("bandpass", $("bandpass").checked ? "1" : "0");
    return fd;
  }

  // ---------- Envío ----------
  async function start(url, fd) {
    clearInterval(pollTimer);
    $("error-section").hidden = true;
    $("results-section").hidden = true;
    $("progress-section").hidden = false;
    setProgress(0, file ? "Subiendo el video…" : "Generando video sintético…");
    $("btn-analizar").disabled = $("btn-demo").disabled = true;
    $("progress-section").scrollIntoView({ behavior: "smooth", block: "center" });
    try {
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.statusText);
      poll(data.job_id);
    } catch (err) {
      showError(err.message);
    }
  }

  $("btn-analizar").addEventListener("click", () => {
    if (!file) return;
    const fd = commonForm();
    fd.append("video", file);
    fd.append("roi_mode", roiMode);
    fd.append("esperado", $("esperado").value);
    start("/api/analizar", fd);
  });

  $("btn-demo").addEventListener("click", () => {
    file = null;
    start("/api/demo", commonForm());
  });

  function setProgress(frac, msg) {
    const pct = Math.round(frac * 100);
    $("bar-fill").style.width = pct + "%";
    $("progress-pct").textContent = pct + " %";
    if (msg) $("progress-msg").textContent = msg;
  }

  function poll(jobId) {
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/estado/${jobId}`);
        const job = await res.json();
        if (!res.ok) throw new Error(job.error);
        setProgress(job.progreso, job.mensaje);
        if (job.estado === "listo") { clearInterval(pollTimer); render(jobId, job.resultado); }
        else if (job.estado === "error") { clearInterval(pollTimer); showError(job.error); }
      } catch (err) { clearInterval(pollTimer); showError(err.message); }
    }, 500);
  }

  function showError(msg) {
    $("progress-section").hidden = true;
    $("error-section").hidden = false;
    $("error-msg").textContent = msg;
    $("btn-analizar").disabled = !file;
    $("btn-demo").disabled = false;
  }

  // ---------- Resultados ----------
  const fmt = (v, d = 2) => (v === null || v === undefined ? "--" : Number(v).toFixed(d));
  const nivel = (q) => (q >= 0.5 ? "alta" : q >= 0.3 ? "media" : "baja");

  function render(jobId, r) {
    $("progress-section").hidden = true;
    $("results-section").hidden = false;
    $("btn-analizar").disabled = !file;
    $("btn-demo").disabled = false;

    const T = r.duration_s;
    $("bpm-pos").textContent = fmt(r.bpm_pos, 1);
    $("bpm-pos-sub").textContent = `pico en ${fmt(r.peak_hz_pos, 3)} Hz · ±${fmt(60 / T / 2, 1)} BPM`;
    $("result-heart").style.animationDuration = (60 / r.bpm_pos).toFixed(3) + "s"; // late a tu ritmo
    $("bpm-verde").innerHTML = `${fmt(r.bpm_verde, 1)}<small> BPM</small>`;
    const q = nivel(r.quality_pos);
    $("calidad").innerHTML = `<span class="q-${q}">${fmt(r.quality_pos)}</span>`;
    $("calidad-sub").textContent = `confiabilidad ${q}`;
    $("resolucion").textContent = fmt(60 / T, 1);
    if (r.expected_bpm !== null && r.expected_bpm !== undefined) {
      $("error").innerHTML = `${r.error_pos >= 0 ? "+" : ""}${fmt(r.error_pos, 1)}<small> BPM</small>`;
      $("error-sub").textContent = `referencia ${fmt(r.expected_bpm, 1)} BPM`;
    } else {
      $("error").textContent = "--";
      $("error-sub").textContent = "sin referencia";
    }
    $("resumen").textContent = r.interpretaciones.resumen;
    $("warnings").innerHTML = (r.warnings || []).map((w) => `<div class="warn">⚠ ${w}</div>`).join("");

    const info = r.info;
    $("tabla-adq").innerHTML = [
      ["fs = FPS", `${fmt(info.fps, 3)} Hz`],
      ["Ts = 1/fs", `${fmt(info.Ts_s * 1000, 2)} ms`],
      ["Nyquist fs/2", `${fmt(info.fps / 2, 2)} Hz`],
      ["Tamaño", `${info.width} × ${info.height} px`],
      ["Fotogramas", info.n_frames_nominal],
      ["Duración total", `${fmt(info.duration_s, 1)} s`],
      ["Duración útil T", `${fmt(T, 1)} s`],
      ["Resolución Δf = 1/T", `${fmt(1 / T, 3)} Hz`],
      ["ROI", r.roi_mode],
      ["Filtro pasa banda", r.use_bandpass ? "sí" : "no"],
    ].map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");

    const cols = [["n_muestras", "N", 0], ["minimo", "mín", 2], ["maximo", "máx", 2],
      ["amplitud_pico_a_pico", "p-p", 2], ["media", "media", 2], ["desv_estandar", "σ", 3]];
    $("tabla-car").innerHTML =
      `<tr><th>Canal</th>${cols.map((c) => `<th>${c[1]}</th>`).join("")}</tr>` +
      Object.entries(r.descripcion_canales).map(([ch, d]) =>
        `<tr><td class="ch-${ch}">${ch}</td>${cols.map((c) => `<td>${fmt(d[c[0]], c[2])}</td>`).join("")}</tr>`).join("");

    const base = `/resultados/${jobId}/`;
    const wide = new Set(["01_roi", "02_rgb_crudo", "07_ruido"]);
    const stamp = Date.now();
    $("figures").innerHTML = Object.entries(r.titulos).map(([key, title], i) => `
      <article class="fig card glass ${wide.has(key) ? "wide" : ""}" style="animation-delay:${i * 80}ms">
        <div class="fig-img"><img src="${base}${r.figuras[key]}?t=${stamp}" alt="${title}" loading="lazy"></div>
        <div class="fig-body">
          <span class="fig-tag">Interpretación</span>
          <h3>${title}</h3>
          <p>${r.interpretaciones[key]}</p>
        </div>
      </article>`).join("");
    document.querySelectorAll(".fig-img img").forEach((img) =>
      img.addEventListener("click", () => { $("lightbox-img").src = img.src; $("lightbox").hidden = false; }));

    $("carpeta").textContent = r.carpeta + "/";
    $("dl-zip").href = `/api/descargar/${jobId}`;
    $("dl-md").href = `${base}reporte.md`;
    $("dl-json").href = `${base}resultados.json`;
    $("results-section").scrollIntoView({ behavior: "smooth" });
  }

  $("lightbox").addEventListener("click", () => ($("lightbox").hidden = true));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("lightbox").hidden = true; });
})();
