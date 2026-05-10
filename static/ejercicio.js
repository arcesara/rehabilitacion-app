// ============================================================
// ejercicio.js — Tiempo real via WebSocket
// ============================================================

const socket = io();

const estadoBanner = document.getElementById('estado-banner');
const estadoTexto  = document.getElementById('estado-texto');
const resumenDiv   = document.getElementById('resumen');
const hrValor      = document.getElementById('hr-valor');
const repsValor    = document.getElementById('reps-valor');
const repsTotalEl  = document.getElementById('reps-total');
const repsBar      = document.getElementById('reps-bar');
const eqIzqEl      = document.getElementById('eq-izq');
const eqDerEl      = document.getElementById('eq-der');
const eqIzqPct     = document.getElementById('eq-izq-pct');
const eqDerPct     = document.getElementById('eq-der-pct');
const resReps      = document.getElementById('res-reps');
const resHr        = document.getElementById('res-hr');
const resDur       = document.getElementById('res-dur');

let repsCompletadas = 0;
let repsTotalNum    = 5;

function actualizarEquilibrio(force_izq, force_der) {
  const sumIzq = force_izq ? Object.values(force_izq).reduce((a,b)=>a+b,0) : 0;
  const sumDer = force_der ? Object.values(force_der).reduce((a,b)=>a+b,0) : 0;
  const total  = sumIzq + sumDer;
  if (total === 0) return;
  const pctIzq = Math.round(sumIzq / total * 100);
  const pctDer = 100 - pctIzq;
  eqIzqEl.style.width  = pctIzq + '%';
  eqDerEl.style.width  = pctDer + '%';
  eqIzqPct.textContent = pctIzq + '%';
  eqDerPct.textContent = pctDer + '%';
}

socket.on('datos_sensores', (datos) => {
  // Heatmap (función definida en ejercicio.html)
  if (window.actualizarHeatmaps) {
    window.actualizarHeatmaps(datos.force_izq, datos.force_der);
  }
  actualizarEquilibrio(datos.force_izq, datos.force_der);
  if (datos.heartrate && datos.heartrate > 0) {
    hrValor.textContent = datos.heartrate;
  }
});

socket.on('sesion_completada', (datos) => {
  resReps.textContent = datos.reps;
  resHr.textContent   = datos.hr_medio;
  resDur.textContent  = Math.round(datos.duracion / 60 * 10) / 10;
  resumenDiv.classList.remove('hidden');
  estadoBanner.className  = 'estado-banner estado-completado';
  estadoTexto.textContent = 'Ejercicio completado';
});

socket.on('rep_completada', (datos) => {
  repsCompletadas       = datos.rep;
  repsTotalNum          = datos.total || repsTotalNum;
  repsValor.textContent = repsCompletadas;
  repsTotalEl.textContent = repsTotalNum;
  const pct = (repsCompletadas / repsTotalNum) * 100;
  repsBar.style.width     = pct + '%';
  estadoBanner.className  = 'estado-banner estado-activo';
  estadoTexto.textContent = `Ejercicio en curso — Rep ${repsCompletadas} / ${repsTotalNum}`;
});

socket.on('touch_detectado', () => {
  estadoBanner.className  = 'estado-banner estado-activo';
  estadoTexto.textContent = 'Identificado — Pulsa START cuando estés listo';
});

socket.on('connect', () => {
  console.log('Conectado al servidor');
});
