// ============================================================
// ejercicio.js — Tiempo real via WebSocket
// Actualiza heatmap, heart rate, repeticiones y equilibrio
// ============================================================

const socket = io();

// --- Referencias DOM ---
const estadoBanner = document.getElementById('estado-banner');
const estadoTexto  = document.getElementById('estado-texto');
const resumenDiv   = document.getElementById('resumen');

// Heart rate
const hrValor = document.getElementById('hr-valor');

// Repeticiones
const repsValor = document.getElementById('reps-valor');
const repsTotal = document.getElementById('reps-total');
const repsBar   = document.getElementById('reps-bar');

// Equilibrio
const eqIzqEl  = document.getElementById('eq-izq');
const eqDerEl  = document.getElementById('eq-der');
const eqIzqPct = document.getElementById('eq-izq-pct');
const eqDerPct = document.getElementById('eq-der-pct');

// Resumen final
const resReps = document.getElementById('res-reps');
const resHr   = document.getElementById('res-hr');
const resDur  = document.getElementById('res-dur');

// Zonas heatmap
const zonas = {
  iz_talon:    document.getElementById('iz-talon'),
  iz_adel_izq: document.getElementById('iz-adel-izq'),
  iz_adel_der: document.getElementById('iz-adel-der'),
  der_talon:   document.getElementById('der-talon'),
  der_adel_izq: document.getElementById('der-adel-izq'),
  der_adel_der: document.getElementById('der-adel-der'),
};
const izTotal  = document.getElementById('iz-total');
const derTotal = document.getElementById('der-total');

// --- Estado local ---
let repsCompletadas = 0;
let repsTotalNum    = 5;  // por defecto, se actualiza cuando llegan datos

// ─── HEATMAP ────────────────────────────────────────────────
// Convierte un valor de fuerza en Newton a un color
// 0N = azul claro, máx = rojo
function fuerzaAColor(newton, maxNewton = 10) {
  const ratio = Math.min(newton / maxNewton, 1);
  if (ratio < 0.33) {
    // Azul → amarillo
    const t = ratio / 0.33;
    const r = Math.round(59  + (234 - 59)  * t);
    const g = Math.round(130 + (179 - 130) * t);
    const b = Math.round(246 + (8   - 246) * t);
    return `rgba(${r},${g},${b},${0.2 + ratio * 0.6})`;
  } else {
    // Amarillo → rojo
    const t = (ratio - 0.33) / 0.67;
    const r = Math.round(234 + (239 - 234) * t);
    const g = Math.round(179 + (68  - 179) * t);
    const b = Math.round(8   + (68  - 8)   * t);
    return `rgba(${r},${g},${b},${0.5 + ratio * 0.5})`;
  }
}

function actualizarHeatmap(force_izq, force_der) {
  if (force_izq) {
    zonas.iz_talon.style.fill    = fuerzaAColor(force_izq.talon_izq    || 0);
    zonas.iz_adel_izq.style.fill = fuerzaAColor(force_izq.adelante_izq || 0);
    zonas.iz_adel_der.style.fill = fuerzaAColor(force_izq.adelante_centro || 0);
    const totalIzq = Object.values(force_izq).reduce((a, b) => a + b, 0);
    izTotal.textContent = totalIzq.toFixed(1);
  }
  if (force_der) {
    zonas.der_talon.style.fill    = fuerzaAColor(force_der.talon_der      || 0);
    zonas.der_adel_izq.style.fill = fuerzaAColor(force_der.adelante_centro || 0);
    zonas.der_adel_der.style.fill = fuerzaAColor(force_der.adelante_der   || 0);
    const totalDer = Object.values(force_der).reduce((a, b) => a + b, 0);
    derTotal.textContent = totalDer.toFixed(1);
  }
}

// ─── EQUILIBRIO ─────────────────────────────────────────────
function actualizarEquilibrio(force_izq, force_der) {
  const sumIzq = force_izq ? Object.values(force_izq).reduce((a,b) => a+b, 0) : 0;
  const sumDer = force_der ? Object.values(force_der).reduce((a,b) => a+b, 0) : 0;
  const total  = sumIzq + sumDer;
  if (total === 0) return;
  const pctIzq = Math.round(sumIzq / total * 100);
  const pctDer = 100 - pctIzq;
  eqIzqEl.style.width  = pctIzq + '%';
  eqDerEl.style.width  = pctDer + '%';
  eqIzqPct.textContent = pctIzq + '%';
  eqDerPct.textContent = pctDer + '%';
}

// ─── WEBSOCKET EVENTOS ──────────────────────────────────────
socket.on('datos_sensores', (datos) => {
  // Actualizar heatmap
  actualizarHeatmap(datos.force_izq, datos.force_der);
  actualizarEquilibrio(datos.force_izq, datos.force_der);

  // Heart rate
  if (datos.heartrate && datos.heartrate > 0) {
    hrValor.textContent = datos.heartrate;
  }
});

socket.on('sesion_completada', (datos) => {
  // Mostrar resumen
  resReps.textContent = datos.reps;
  resHr.textContent   = datos.hr_medio;
  resDur.textContent  = Math.round(datos.duracion / 60 * 10) / 10;

  resumenDiv.classList.remove('hidden');
  estadoBanner.className = 'estado-banner estado-completado';
  estadoTexto.textContent = '✅ Ejercicio completado';
});

// Escuchar repeticiones desde el servidor si se retransmiten
socket.on('rep_completada', (datos) => {
  repsCompletadas = datos.rep;
  repsTotalNum    = datos.total || repsTotalNum;
  repsValor.textContent = repsCompletadas;
  repsTotal.textContent = repsTotalNum;
  const pct = (repsCompletadas / repsTotalNum) * 100;
  repsBar.style.width = pct + '%';

  // Actualizar estado
  estadoBanner.className = 'estado-banner estado-activo';
  estadoTexto.textContent = `🏃 Ejercicio en curso — Rep ${repsCompletadas} / ${repsTotalNum}`;
});

socket.on('touch_detectado', () => {
  estadoBanner.className = 'estado-banner estado-activo';
  estadoTexto.textContent = '✅ Identificado — Pulsa START cuando estés listo';
});

socket.on('connect', () => {
  console.log('Conectado al servidor');
});
