// ============================================================
// ejercicio.js — Tiempo real via WebSocket
// Gestiona heatmap, métricas y progresión de niveles
// ============================================================

const socket = io();

const estadoBanner   = document.getElementById('estado-banner');
const estadoTexto    = document.getElementById('estado-texto');
const resumenDiv     = document.getElementById('resumen');
const hrValor        = document.getElementById('hr-valor');
const repsValorEl    = document.getElementById('reps-valor');
const repsTotalEl    = document.getElementById('reps-total');
const repsBar        = document.getElementById('reps-bar');
const eqIzqEl        = document.getElementById('eq-izq');
const eqDerEl        = document.getElementById('eq-der');
const eqIzqPct       = document.getElementById('eq-izq-pct');
const eqDerPct       = document.getElementById('eq-der-pct');
const resReps        = document.getElementById('res-reps');
const resHr          = document.getElementById('res-hr');
const resDur         = document.getElementById('res-dur');
const resumenAcciones = document.getElementById('resumen-acciones');

let repsCompletadas = 0;

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

  // Generar botones de acción según el nivel completado
  let html = '';
  if (datos.completada && datos.siguiente_nivel <= 5) {
    html += `<a href="/ejercicio/${datos.ejercicio_id}/${datos.siguiente_nivel}" class="btn-primary">
      Subir a nivel ${datos.siguiente_nivel}
    </a>`;
  }
  html += `<a href="/ejercicio/${datos.ejercicio_id}/${datos.nivel_actual}" class="btn-secondary">
    Repetir nivel ${datos.nivel_actual}
  </a>`;
  html += `<a href="/ejercicios" class="btn-secondary">Ver todos los ejercicios</a>`;
  resumenAcciones.innerHTML = html;
});

socket.on('rep_completada', (datos) => {
  repsCompletadas = datos.rep;
  repsValorEl.textContent = repsCompletadas;
  const total = REPS_TOTAL || parseInt(repsTotalEl.textContent) || 5;
  const pct = (repsCompletadas / total) * 100;
  repsBar.style.width = pct + '%';
  estadoBanner.className  = 'estado-banner estado-activo';
  estadoTexto.textContent = `Ejercicio en curso — Rep ${repsCompletadas} / ${total}`;
});

socket.on('touch_detectado', () => {
  estadoBanner.className  = 'estado-banner estado-activo';
  estadoTexto.textContent = 'Identificado — Pulsa START cuando estés listo';
});

socket.on('connect', () => {
  console.log('Conectado al servidor');
});
