/* ===== STATE ===== */
const state = {
  simRunning: true,
  irradiance: 0,
  buffer: [],
  maxBuffer: 50000,
  homeChartZoom: 1,
  minVal: Infinity,
  maxVal: -Infinity,
  sumVal: 0,
  countVal: 0,
  diagConnected: false,
  diagAutoRead: true,
  davisConnected: false,
  davisLastRead: null,
  davisWeather: null,
  davisStatus: null,
  lastEnergyAt: null,
  siteEnergyKwhM2: 0,
  panelAreaM2: 1,
  panelEfficiency: 0.18,
  groupHistory: [],
  maxGroupHistory: 50000,
  activeDatabase: {
    path: './data/nexo_solar.db',
    analysisTable: 'davis_weather_readings',
  },
  sqliteMode: 'existing',
  graphRangeHours: 1,
  graphZoom: {
    solar: 1,
    temp: 1,
    humidity: 1,
    wind: 1,
    rain: 1,
  },
  diagUpdateCount: 0,
  docMode: 'html',
};

/* ===== INIT ===== */
window.addEventListener('DOMContentLoaded', () => {
  initGauge();
  initChart();
  initGroupCharts();
  initLog();
  initDiagLog();
  loadDoc();
  updateLocationInfo();
  updateHomeSummary();
  updatePanelConfig();
  // Use the Python backend if embedded in QWebEngine; otherwise simulate.
  if (!initBridge()) startSimulation();
});

/* ===== TABS ===== */
function switchTab(name) {
  const tabs = ['inicio', 'davis', 'graficas', 'ubicacion', 'datos', 'diagnostico', 'configuracion', 'documentacion'];
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', tabs[i] === name);
  });
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  const title = document.getElementById('viewTitle');
  if (title) title.textContent = tabsLabel(name);

  if (name === 'ubicacion') refreshMapSize();

  if (name === 'datos') {
    initAnalysisCanvases();
    populateTableSelect();
    if (!anaData.length) loadAnalysisData(); else renderAll();
  }

  if (name === 'graficas') {
    loadDavisHistory();
    drawGroupCharts();
  }
}

function tabsLabel(name) {
  const labels = {
    inicio: 'Inicio',
    davis: 'Estación Davis',
    graficas: 'Gráficas',
    ubicacion: 'Ubicación',
    datos: 'Datos',
    diagnostico: 'Diagnóstico',
    configuracion: 'Configuración',
    documentacion: 'Documentación',
  };
  return labels[name] || 'Nexo Solar';
}

/* ===== GAUGE ===== */
let gaugeCtx;
function initGauge() {
  const canvas = document.getElementById('gaugeCanvas');
  gaugeCtx = canvas.getContext('2d');
  drawGauge(state.irradiance);
}

function drawGauge(value) {
  const c = gaugeCtx;
  const canvas = document.getElementById('gaugeCanvas');
  const W = canvas.width, H = canvas.height;
  c.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H - 20;
  const r = Math.min(130, W / 2 - 28, H - 42);

  // Track background
  c.beginPath();
  c.arc(cx, cy, r, Math.PI, 0);
  c.lineWidth = 18;
  c.strokeStyle = '#21262d';
  c.stroke();

  // Colored arc segments
  const segments = [
    { from: 0, to: 400, color: '#3fb950' },
    { from: 400, to: 800, color: '#a8d672' },
    { from: 800, to: 1200, color: '#d29922' },
    { from: 1200, to: 1600, color: '#f0883e' },
    { from: 1600, to: 2000, color: '#f78166' },
  ];
  segments.forEach(seg => {
    const a1 = Math.PI + (seg.from / 2000) * Math.PI;
    const a2 = Math.PI + (seg.to / 2000) * Math.PI;
    c.beginPath();
    c.arc(cx, cy, r, a1, a2);
    c.lineWidth = 18;
    c.strokeStyle = seg.color;
    c.stroke();
  });

  // Tick marks
  c.lineWidth = 2;
  [0, 400, 800, 1200, 1600, 2000].forEach(v => {
    const a = Math.PI + (v / 2000) * Math.PI;
    const ix = cx + (r - 22) * Math.cos(a), iy = cy + (r - 22) * Math.sin(a);
    const ox = cx + (r + 4) * Math.cos(a), oy = cy + (r + 4) * Math.sin(a);
    c.beginPath(); c.moveTo(ix, iy); c.lineTo(ox, oy);
    c.strokeStyle = '#8b949e'; c.stroke();
    const tx = cx + (r + 18) * Math.cos(a), ty = cy + (r + 18) * Math.sin(a);
    c.fillStyle = '#8b949e'; c.font = '10px Segoe UI';
    c.textAlign = 'center'; c.textBaseline = 'middle';
    c.fillText(v, tx, ty);
  });

  // Needle
  const ratio = Math.min(value, 2000) / 2000;
  const needleA = Math.PI + ratio * Math.PI;
  const nx = cx + (r - 30) * Math.cos(needleA), ny = cy + (r - 30) * Math.sin(needleA);
  c.beginPath(); c.moveTo(cx, cy); c.lineTo(nx, ny);
  c.lineWidth = 4; c.strokeStyle = '#17211b'; c.lineCap = 'round'; c.stroke();

  // Center dot
  c.beginPath(); c.arc(cx, cy, 7, 0, Math.PI * 2);
  c.fillStyle = '#1f6feb'; c.fill();
}

/* ===== CHART ===== */
let chartCtx;
function initChart() {
  const canvas = document.getElementById('chartCanvas');
  chartCtx = canvas.getContext('2d');
  prepareScrollableCanvas(canvas, state.homeChartZoom, 0);
}

function drawChart() {
  const canvas = document.getElementById('chartCanvas');
  const data = state.buffer.filter(value => Number.isFinite(value));
  const size = prepareScrollableCanvas(canvas, state.homeChartZoom, data.length);
  const c = chartCtx;
  const W = size.width, H = 260;
  c.clearRect(0, 0, W, H);
  const pad = { top: 16, right: 16, bottom: 32, left: 48 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;

  const maxY = getHomeChartMax(data);

  // Grid
  c.strokeStyle = '#21262d'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * iH;
    c.beginPath(); c.moveTo(pad.left, y); c.lineTo(W - pad.right, y); c.stroke();
    const val = Math.round(maxY - (i / 4) * maxY);
    c.fillStyle = '#6e7681'; c.font = '10px Segoe UI'; c.textAlign = 'right';
    c.fillText(val, pad.left - 6, y + 4);
  }

  if (!data.length) {
    drawEmptyHomeChart(c, W, H, 'Esperando lecturas Davis');
    return;
  }

  if (data.length === 1) {
    const y = pad.top + (1 - Math.min(data[0], maxY) / maxY) * iH;
    c.beginPath();
    c.arc(pad.left + iW / 2, y, 4, 0, Math.PI * 2);
    c.fillStyle = '#1f6feb';
    c.fill();
    drawHomeChartLabel(c, W, H);
    return;
  }

  // Gradient fill
  const grad = c.createLinearGradient(0, pad.top, 0, H - pad.bottom);
  grad.addColorStop(0, 'rgba(88,166,255,0.3)');
  grad.addColorStop(1, 'rgba(88,166,255,0)');

  c.beginPath();
  data.forEach((v, i) => {
    const x = pad.left + (i / (data.length - 1)) * iW;
    const y = pad.top + (1 - Math.min(v, maxY) / maxY) * iH;
    i === 0 ? c.moveTo(x, y) : c.lineTo(x, y);
  });
  c.strokeStyle = '#1f6feb'; c.lineWidth = 2; c.stroke();

  // Fill
  const lastX = pad.left + iW, firstX = pad.left;
  c.lineTo(lastX, H - pad.bottom);
  c.lineTo(firstX, H - pad.bottom);
  c.closePath();
  c.fillStyle = grad; c.fill();

  drawHomeChartLabel(c, W, H);
}

function drawEmptyHomeChart(ctx, width, height, message) {
  ctx.fillStyle = '#697463';
  ctx.font = '12px Segoe UI';
  ctx.textAlign = 'center';
  ctx.fillText(message, width / 2, height / 2);
  drawHomeChartLabel(ctx, width, height);
}

function drawHomeChartLabel(ctx, width, height) {
  ctx.fillStyle = '#6e7681';
  ctx.font = '10px Segoe UI';
  ctx.textAlign = 'center';
  ctx.fillText('Histórico acumulado de lecturas Davis', width / 2, height - 4);
}

function getHomeChartMax(data) {
  const values = data.filter(v => Number.isFinite(v) && v >= 0);
  if (Number.isFinite(state.irradiance) && state.irradiance >= 0) values.push(state.irradiance);
  const observed = values.length ? Math.max(...values) : 100;
  if (observed <= 80) return 100;
  if (observed <= 160) return 200;
  if (observed <= 400) return 500;
  if (observed <= 800) return 1000;
  if (observed <= 1200) return 1400;
  return Math.max(2000, Math.ceil(observed / 500) * 500);
}

function zoomHomeChart(direction) {
  state.homeChartZoom = clampZoom(state.homeChartZoom + direction * 0.25);
  setText('homeChartZoomLabel', `${Math.round(state.homeChartZoom * 100)}%`);
  drawChart();
}

function resetHomeChartZoom() {
  state.homeChartZoom = 1;
  setText('homeChartZoomLabel', '100%');
  drawChart();
}

function clampZoom(value) {
  return Math.max(0.5, Math.min(8, value));
}

function prepareScrollableCanvas(canvas, zoom, sampleCount) {
  const viewport = canvas.closest('.chart-scroll') || canvas.parentElement;
  const viewportWidth = Math.max(280, viewport?.clientWidth || canvas.parentElement?.clientWidth || 600);
  const height = parseInt(canvas.getAttribute('height'), 10) || 220;
  const step = sampleCount > 1 ? Math.max(3, 7 * zoom) : viewportWidth;
  const targetWidth = Math.ceil(Math.max(viewportWidth, 72 + Math.max(sampleCount - 1, 1) * step));
  const keepAtEnd = viewport ? viewport.scrollLeft + viewport.clientWidth >= viewport.scrollWidth - 12 : true;
  const previousLeft = viewport?.scrollLeft || 0;

  canvas.width = targetWidth;
  canvas.height = height;

  if (viewport) {
    requestAnimationFrame(() => {
      viewport.scrollLeft = keepAtEnd ? viewport.scrollWidth : Math.min(previousLeft, viewport.scrollWidth);
    });
  }

  return { width: targetWidth, height, viewportWidth };
}

/* ===== SIMULATION ===== */
let simInterval;
function startSimulation() {
  simInterval = setInterval(tick, 1000);
}

function tick() {
  if (!state.simRunning) return;
  // Simulate realistic irradiance with noise
  const hour = new Date().getHours() + new Date().getMinutes() / 60;
  const solar = Math.max(0, Math.sin(Math.PI * (hour - 6) / 12) * 1200);
  const noise = (Math.random() - 0.5) * 120;
  applyIrradiance(Math.max(0, Math.min(2000, solar + noise)));
}

// Apply one irradiance value from the active source. Davis weather rows arrive
// through updateDavisWeather(); this function must not invent station data.
function applyIrradiance(value) {
  const cleanValue = normalizeIrradiance(value);
  if (cleanValue === null) return;
  integrateSolarEnergy(cleanValue);
  state.irradiance = cleanValue;

  state.buffer.push(cleanValue);
  trimArrayStart(state.buffer, state.maxBuffer);

  // Stats
  if (cleanValue < state.minVal) state.minVal = cleanValue;
  if (cleanValue > state.maxVal) state.maxVal = cleanValue;
  state.sumVal += cleanValue; state.countVal++;

  updateMonitorUI();
  updateHomeSummary();
  if (state.diagConnected && state.diagAutoRead) updateDiagUI();
}

function integrateSolarEnergy(value) {
  const now = Date.now();
  if (state.lastEnergyAt) {
    const elapsedHours = Math.min((now - state.lastEnergyAt) / 3600000, 1 / 12);
    state.siteEnergyKwhM2 += Math.max(value, 0) * elapsedHours / 1000;
  }
  state.lastEnergyAt = now;
}

function normalizeIrradiance(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.max(0, n);
}

function trimArrayStart(items, maxLength) {
  if (items.length > maxLength) items.splice(0, items.length - maxLength);
}

/* ===== PYTHON BRIDGE (QWebChannel) ===== */
let bridge = null;

function initBridge() {
  if (!(window.qt && window.qt.webChannelTransport) || typeof QWebChannel === 'undefined') {
    return false; // plain browser → keep the standalone simulation
  }
  try {
    new QWebChannel(qt.webChannelTransport, function (channel) {
      bridge = channel.objects.bridge;
      bridge.irradianceUpdated.connect(function (v) { applyIrradiance(v); });
      bridge.logMessage.connect(function (src, lvl, txt) {
        const msg = (src ? '[' + src + '] ' : '') + txt;
        addLog(msg, lvl || 'info');
        diagLog(msg, lvl || 'info');
      });
      bridge.connectionChanged.connect(setConnectionUI);
      bridge.safeStateChanged.connect(setSafeStateUI);
      if (bridge.davisWeatherUpdated) bridge.davisWeatherUpdated.connect(updateDavisWeather);
      if (bridge.davisConnectionChanged) bridge.davisConnectionChanged.connect(setDavisConnectionUI);
      if (bridge.davisStatusUpdated) bridge.davisStatusUpdated.connect(updateDavisStatus);
      if (bridge.davisRetryExhausted) {
        bridge.davisRetryExhausted.connect(function (operation, error) {
          setDavisConnectionUI(false, `${operation}: ${error}`);
        });
      }
      addLog('[SISTEMA] Conectado al backend (bridge activo)', 'info');
      refreshDavisStatus();
      loadDavisHistory();
    });
    return true;
  } catch (e) {
    console.error('initBridge failed', e);
    return false;
  }
}

// Drive the connection UI from a backend signal.
function setConnectionUI(connected) {
  state.diagConnected = !!connected;
  const btn = document.getElementById('diagConnBtn');
  const led = document.getElementById('diagLedConn');
  const sensorLed = document.getElementById('diagLedSensor');
  const estado = document.getElementById('diagEstado');
  const connDot = document.getElementById('connDot');
  const shellStatus = document.getElementById('shellStatusText');
  if (connected) {
    if (btn) { btn.textContent = 'Desconectar'; btn.className = 'btn btn-danger full-width'; }
    if (led) led.className = 'led green';
    if (sensorLed) sensorLed.className = 'led green';
    if (estado) estado.textContent = 'Conectado';
    if (connDot) connDot.className = 'status-dot green';
    if (shellStatus) shellStatus.textContent = 'Conectado';
  } else {
    if (btn) { btn.textContent = 'Conectar'; btn.className = 'btn btn-primary full-width'; }
    if (led) led.className = 'led red';
    if (sensorLed) sensorLed.className = 'led red';
    if (estado) estado.textContent = 'Desconectado';
    if (connDot) connDot.className = 'status-dot red';
    if (shellStatus) shellStatus.textContent = 'Desconectado';
  }
}

function setSafeStateUI(inSafe) {
  const led = document.getElementById('sysLed');
  const txt = document.getElementById('sysStateText');
  const recBtn = document.getElementById('recoveryBtn');
  if (inSafe) {
    if (led) led.className = 'led red';
    if (txt) txt.textContent = 'Estado: MODO SEGURO';
    if (recBtn) recBtn.classList.remove('hidden');
    addLog('[SISTEMA] MODO SEGURO activado', 'warn');
  } else {
    if (led) led.className = 'led green';
    if (txt) txt.textContent = 'Estado: Normal';
    if (recBtn) recBtn.classList.add('hidden');
  }
}

function setDavisConnectionUI(connected, message) {
  state.davisConnected = !!connected;
  const led = document.getElementById('davisLed');
  const text = document.getElementById('davisState');
  const btn = document.getElementById('davisConnectBtn');
  if (led) led.className = 'led ' + (connected ? 'green' : 'red');
  if (text) text.textContent = message || (connected ? 'Conectado' : 'Desconectado');
  if (btn) btn.disabled = !!connected;
  updateDavisDiagnostic();
  updateHomeSummary();
}

function updateDavisWeather(data) {
  state.davisLastRead = new Date();
  state.davisWeather = data || {};
  state.davisConnected = true;
  if (typeof data.solar_radiation_wm2 === 'number') applyIrradiance(data.solar_radiation_wm2);
  pushGroupHistory(state.davisWeather);
  updateDavisStatus({
    connected: true,
    read_count: Math.max((state.davisStatus?.read_count || 0) + 1, state.groupHistory.length),
    last_error: '',
    last_reading: state.davisWeather,
  });
  setDavisValue('weatherSolar', data.solar_radiation_wm2, ' W/m²', 0);
  setDavisValue('weatherTempOut', data.temp_out_c, ' °C', 1);
  setDavisValue('weatherTempIn', data.temp_in_c, ' °C', 1);
  setDavisValue('weatherHumidityOut', data.humidity_out, ' %', 0);
  setDavisValue('weatherHumidityIn', data.humidity_in, ' %', 0);
  setDavisValue('weatherPressure', data.pressure_hpa, ' hPa', 1);
  setDavisValue('weatherWind', data.wind_speed_ms, ' m/s', 2);
  setDavisValue('weatherWindAvg', data.wind_speed_avg_ms, ' m/s', 2);
  setDavisValue('weatherWindDir', data.wind_dir_deg, ' °', 0);
  setDavisValue('weatherRainRate', data.rain_rate_mm, ' mm', 2);
  setDavisValue('weatherRainStorm', data.rain_storm_mm, ' mm', 2);
  setDavisValue('weatherRainDay', data.rain_day_mm, ' mm', 2);
  setDavisValue('weatherRainMonth', data.rain_month_mm, ' mm', 2);
  setDavisValue('weatherRainYear', data.rain_year_mm, ' mm', 2);
  setDavisValue('weatherUv', data.uv_index, '', 1);
  const last = document.getElementById('davisLastRead');
  if (last) last.textContent = 'Última lectura: ' + state.davisLastRead.toLocaleTimeString('es-CO', { hour12: false });
  updateHomeSummary();
  drawGroupCharts();
}

function refreshDavisStatus() {
  if (!bridge || !bridge.getDavisStatus) return;
  bridge.getDavisStatus(function (status) {
    updateDavisStatus(status || {});
    if (status && status.last_reading && Object.keys(status.last_reading).length) {
      updateDavisWeather(status.last_reading);
    }
  });
}

function updateDavisStatus(status) {
  state.davisStatus = { ...(state.davisStatus || {}), ...(status || {}) };
  if (typeof state.davisStatus.connected === 'boolean') {
    state.davisConnected = state.davisStatus.connected;
  }
  const led = document.getElementById('davisLed');
  const text = document.getElementById('davisState');
  const isSerial = (state.davisStatus?.transport || 'serial') === 'serial';
  if (led) led.className = 'led ' + (state.davisConnected ? 'green' : 'red');
  if (text) text.textContent = state.davisConnected ? (isSerial ? 'Conectada por USB' : 'Conectada por IP') : 'Desconectada';
  updateDavisDiagnostic();
  updateHomeSummary();
}

function setDavisValue(id, value, unit, digits) {
  const el = document.getElementById(id);
  if (!el) return;
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    el.textContent = '--' + unit;
    return;
  }
  el.textContent = value.toFixed(digits) + unit;
}

function fmtValue(value, digits = 1, fallback = '--') {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : fallback;
}

function updatePanelConfig() {
  const area = parseFloat(document.getElementById('panelAreaInput')?.value);
  const efficiencyPercent = parseFloat(document.getElementById('panelEfficiencyInput')?.value);
  if (Number.isFinite(area) && area > 0) state.panelAreaM2 = area;
  if (Number.isFinite(efficiencyPercent) && efficiencyPercent > 0) {
    state.panelEfficiency = efficiencyPercent / 100;
  }
  updateHomeSummary();
}

function updateHomeSummary() {
  const panelEnergy = state.siteEnergyKwhM2 * state.panelAreaM2 * state.panelEfficiency;
  const siteEl = document.getElementById('siteEnergyDisplay');
  const panelEl = document.getElementById('panelEnergyDisplay');
  const panelSub = document.getElementById('panelEnergySub');
  const lastPill = document.getElementById('lastReadPill');
  const davisState = document.getElementById('homeDavisState');
  const davisLast = document.getElementById('homeDavisLast');
  const weatherSummary = document.getElementById('homeWeatherSummary');
  const windSummary = document.getElementById('homeWindSummary');

  if (siteEl) siteEl.textContent = (state.siteEnergyKwhM2 * 1000).toFixed(3) + ' Wh/m²';
  if (panelEl) panelEl.textContent = panelEnergy.toFixed(3) + ' kWh';
  if (panelSub) panelSub.textContent = `${state.panelAreaM2.toFixed(2)} m² · ${(state.panelEfficiency * 100).toFixed(1)}% eficiencia`;

  const lastLabel = state.davisLastRead
    ? state.davisLastRead.toLocaleTimeString('es-CO', { hour12: false })
    : '--';
  if (lastPill) lastPill.textContent = lastLabel;
  if (davisState) davisState.textContent = state.davisConnected ? 'Conectada USB' : 'Sin conexión USB';
  if (davisLast) {
    davisLast.textContent = state.davisLastRead ? `Última lectura: ${lastLabel}` : 'Sin lectura registrada';
  }

  const data = state.davisWeather || {};
  if (weatherSummary) {
    weatherSummary.textContent = `${fmtValue(data.temp_out_c, 1)} °C · ${fmtValue(data.humidity_out, 0)} %`;
  }
  if (windSummary) windSummary.textContent = `Viento ${fmtValue(data.wind_speed_ms, 2)} m/s`;
}

function connectDavis() {
  if (!bridge || !bridge.connectDavis) {
    setDavisConnectionUI(false, 'Backend Davis no disponible');
    return;
  }
  const transport = document.getElementById('davisTransport').value;
  const serialPort = document.getElementById('davisSerialPort').value;
  const ipHost = document.getElementById('davisIpHost').value;
  const ipPort = parseInt(document.getElementById('davisIpPort').value, 10) || 22222;
  setDavisConnectionUI(false, 'Conectando...');
  bridge.connectDavis(transport, serialPort, ipHost, ipPort, function (ok) {
    if (!ok) setDavisConnectionUI(false, 'No se pudo conectar');
  });
}

function disconnectDavis() {
  if (bridge && bridge.disconnectDavis) bridge.disconnectDavis();
  setDavisConnectionUI(false, 'Desconectado');
}

function readDavisOnce() {
  if (!state.davisConnected) {
    showToast('Davis no conectado', 'error');
    return;
  }
  if (bridge && bridge.readDavisOnce) bridge.readDavisOnce();
}

function loadDavisHistory() {
  if (!bridge || !bridge.loadDavisHistory) return;
  bridge.loadDavisHistory(0, function (rows) {
    if (!Array.isArray(rows) || !rows.length) {
      state.groupHistory = [];
      state.buffer = [];
      rebuildIrradianceStats([]);
      updateMonitorUI();
      drawGroupCharts();
      return;
    }
    state.groupHistory = rows.map(normalizeDavisHistoryRow);
    syncHomeIrradianceFromHistory(state.groupHistory);
    drawGroupCharts();
  });
}

function normalizeDavisHistoryRow(row) {
  return {
    t: row.timestamp ? new Date(row.timestamp) : new Date(),
    solar: row.solar_radiation_wm2,
    uv: row.uv_index,
    tempOut: row.temp_out_c,
    tempIn: row.temp_in_c,
    humidityOut: row.humidity_out,
    humidityIn: row.humidity_in,
    pressure: row.pressure_hpa,
    wind: row.wind_speed_ms,
    windAvg: row.wind_speed_avg_ms,
    windDir: row.wind_dir_deg,
    rainRate: row.rain_rate_mm,
    rainStorm: row.rain_storm_mm,
    rainDay: row.rain_day_mm,
    rainMonth: row.rain_month_mm,
    rainYear: row.rain_year_mm,
    siteEnergy: row.site_energy_kwh_m2,
    panelEnergy: row.estimated_panel_energy_kwh,
  };
}

function updateMonitorUI() {
  document.getElementById('irradDisplay').textContent = state.irradiance.toFixed(2);
  drawGauge(state.irradiance);
  drawChart();
  document.getElementById('statMin').textContent = state.minVal === Infinity ? '0' : state.minVal.toFixed(0);
  document.getElementById('statMax').textContent = state.maxVal === -Infinity ? '0' : state.maxVal.toFixed(0);
  document.getElementById('statAvg').textContent = state.countVal ? (state.sumVal / state.countVal).toFixed(0) : '0';
}

function syncHomeIrradianceFromHistory(rows) {
  const values = rows
    .map(row => normalizeIrradiance(row.solar))
    .filter(value => value !== null);
  if (!values.length) return;

  state.buffer = values.slice(-state.maxBuffer);
  state.irradiance = state.buffer[state.buffer.length - 1];
  rebuildIrradianceStats(state.buffer);
  updateMonitorUI();
  updateHomeSummary();
}

function rebuildIrradianceStats(values) {
  state.minVal = Infinity;
  state.maxVal = -Infinity;
  state.sumVal = 0;
  state.countVal = 0;
  values.forEach(value => {
    if (value < state.minVal) state.minVal = value;
    if (value > state.maxVal) state.maxVal = value;
    state.sumVal += value;
    state.countVal += 1;
  });
}

function toggleSimulation() {
  state.simRunning = !state.simRunning;
  document.getElementById('simBtnIcon').textContent = state.simRunning ? '⏸' : '▶';
  document.getElementById('simBtnText').textContent = state.simRunning ? 'Pausar Simulación' : 'Reanudar Simulación';
  addLog(state.simRunning ? 'Lectura reanudada' : 'Lectura pausada', 'warn');
  if (bridge) { state.simRunning ? bridge.resumeReading() : bridge.pauseReading(); }
}

/* ===== LOG ===== */
function initLog() {
  addLog('[SISTEMA] Nexo Solar iniciado correctamente', 'info');
}

function addLog(msg, type = '') {
  const el = document.getElementById('logConsole');
  const line = document.createElement('span');
  line.className = 'log-line' + (type ? ' ' + type : '');
  const ts = new Date().toLocaleTimeString('es-CO', { hour12: false });
  line.textContent = `[${ts}] ${msg}`;
  el.appendChild(line);
  el.appendChild(document.createElement('br'));
  el.scrollTop = el.scrollHeight;
}

function clearLog() {
  document.getElementById('logConsole').innerHTML = '';
}

/* ===== SAFE STATE ===== */
function exitSafeState() {
  if (bridge) bridge.recoverSafeState();
  document.getElementById('sysLed').className = 'led green';
  document.getElementById('sysStateText').textContent = 'Estado: Normal';
  document.getElementById('recoveryBtn').classList.add('hidden');
  addLog('[SISTEMA] Saliendo del MODO SEGURO - Operaciones habilitadas', 'info');
  showToast('Sistema recuperado correctamente');
}

/* ===== SQLITE MODAL ===== */
function openSQLiteModal() {
  refreshActiveDatabase();
  document.getElementById('sqliteModal').classList.remove('hidden');
}
function closeSQLiteModal() {
  document.getElementById('sqliteModal').classList.add('hidden');
}
function browseExistingDB() {
  if (bridge) {
    bridge.browseExistingDbFile(function (p) {
      if (p) {
        state.sqliteMode = 'existing';
        document.getElementById('dbPath').value = p;
        document.getElementById('newTableName').value = '';
        document.getElementById('dbModeHint').textContent = 'Base existente seleccionada. No se crearán registros de prueba.';
      }
    });
    return;
  }
  document.getElementById('dbPath').value = './data/nexo_solar.db';
}
function browseNewDB() {
  if (bridge) {
    bridge.browseNewDbFile(function (p) {
      if (p) {
        state.sqliteMode = 'new';
        document.getElementById('dbPath').value = p;
        document.getElementById('newTableName').value = 'mediciones';
        document.getElementById('dbModeHint').textContent = 'Base nueva seleccionada. Se creará vacía y Davis registrará lecturas reales.';
      }
    });
    return;
  }
  state.sqliteMode = 'new';
  document.getElementById('dbPath').value = './data/nexo_solar_' + new Date().getFullYear() + '.db';
  document.getElementById('newTableName').value = 'mediciones';
}
function acceptSQLite() {
  const path = document.getElementById('dbPath').value;
  const selectedTable = document.getElementById('tableSelect').value;
  const table = document.getElementById('newTableName').value || selectedTable || 'mediciones';
  const openExistingOnly = state.sqliteMode === 'existing' && !document.getElementById('newTableName').value;
  if (!openExistingOnly && (!table || table === '-- Seleccionar tabla --')) {
    showToast('Selecciona o crea una tabla', 'error'); return;
  }
  if (bridge) {
    const done = function (ok) {
      closeSQLiteModal();
      if (ok) {
        addLog(`[SQLite] Base de datos activa: ${path}${openExistingOnly ? '' : ' → tabla: ' + table}`, 'info');
        showToast('Base de datos configurada correctamente');
        refreshActiveDatabase();
        populateTableSelect();
        loadDavisHistory();
        if (document.getElementById('tab-datos').classList.contains('active')) loadAnalysisData();
      } else {
        addLog('[SQLite] Error configurando la base de datos', 'error');
        showToast('Error configurando SQLite', 'error');
      }
    };
    if (openExistingOnly && bridge.connectExistingSqlite) bridge.connectExistingSqlite(path, done);
    else bridge.configureSqlite(path, table, done);
    return;
  }
  closeSQLiteModal();
  addLog(`[SQLite] Base de datos configurada: ${path} → tabla: ${table}`, 'info');
  showToast('Base de datos configurada correctamente');
}

function refreshActiveDatabase() {
  if (!bridge || !bridge.getActiveDatabase) return;
  bridge.getActiveDatabase(function (db) {
    if (!db) return;
    state.activeDatabase = db;
    const dbPathInput = document.getElementById('dbPath');
    if (dbPathInput) dbPathInput.value = db.path || state.activeDatabase.path;
    const tableInput = document.getElementById('newTableName');
    if (tableInput) tableInput.value = '';
    const hint = document.getElementById('dbModeHint');
    if (hint) hint.textContent = `Base activa: ${db.path || '--'} · tabla Davis: ${db.davis_table || 'davis_weather_readings'}`;
    const activeDbLabel = document.getElementById('anaActiveDb');
    if (activeDbLabel) activeDbLabel.textContent = db.path || '--';
  });
}

/* ===== TOAST ===== */
function showToast(msg, type = 'ok') {
  const t = document.getElementById('toast');
  t.textContent = (type === 'error' ? '⚠ ' : '✓ ') + msg;
  t.style.borderColor = type === 'error' ? 'var(--accent3)' : 'var(--accent2)';
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3000);
}

/* ===== MAPA =====
 * La fuente de tiles esta abstraida a proposito: hoy solo devuelve la capa
 * online, pero cuando exista el paquete offline elegido por el usuario basta
 * con que tileSource() devuelva la plantilla local. Nada mas cambia.
 */
const MAP_SOURCES = {
  online: {
    id: 'online',
    label: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  },
  // offline: { id:'offline', label:'Paquete sin conexión', url:'packs/{pack}/{z}/{x}/{y}.png', ... }
};

const mapState = {
  map: null,
  marker: null,
  layer: null,
  ready: false,
  syncing: false,   // evita el bucle marcador <-> inputs
  observer: null,
  tileErrors: 0,
};

/** Devuelve la fuente de tiles activa. Unico punto a tocar para offline. */
function tileSource() {
  return MAP_SOURCES.online;
}

function showMapState(show, title, msg) {
  const el = document.getElementById('mapState');
  if (!el) return;
  if (show) {
    document.getElementById('mapStateTitle').textContent = title;
    document.getElementById('mapStateMsg').textContent = msg;
    el.removeAttribute('hidden');
  } else {
    el.setAttribute('hidden', '');
  }
}

function currentCoords() {
  const lat = parseFloat(document.getElementById('latInput').value);
  const lon = parseFloat(document.getElementById('lonInput').value);
  return [Number.isFinite(lat) ? lat : 0, Number.isFinite(lon) ? lon : 0];
}

function initMap() {
  if (mapState.ready) return;
  if (typeof L === 'undefined') {
    console.error('[MAPA] Leaflet no cargó: window.L es undefined. Revisar vendor/leaflet/leaflet.js');
    showMapState(true, 'Mapa no disponible', 'No se pudo cargar la librería de mapas (Leaflet).');
    return;
  }
  const host = document.getElementById('map');
  if (!host) {
    console.error('[MAPA] No existe el contenedor #map en el DOM');
    return;
  }
  console.log('[MAPA] initMap: contenedor ' + host.clientWidth + 'x' + host.clientHeight);

  const [lat, lon] = currentCoords();
  const src = tileSource();

  mapState.map = L.map(host, { zoomControl: true, attributionControl: true })
                  .setView([lat, lon], 13);

  mapState.layer = L.tileLayer(src.url, {
    maxZoom: src.maxZoom,
    attribution: src.attribution,
  }).addTo(mapState.map);

  // Si los tiles no bajan, lo decimos. Nada de cuadro vacio sin explicacion.
  mapState.layer.on('tileerror', () => {
    mapState.tileErrors++;
    if (mapState.tileErrors > 3) {
      showMapState(true, 'Sin conexión',
        'No se pudieron descargar los mapas. Las coordenadas siguen siendo válidas para configurar la ubicación del equipo.');
      document.getElementById('mapSource').textContent = 'Mapa no disponible';
    }
  });
  mapState.layer.on('load', () => {
    mapState.tileErrors = 0;
    showMapState(false);
    document.getElementById('mapSource').textContent = tileSource().label;
  });

  mapState.marker = L.marker([lat, lon], { draggable: true }).addTo(mapState.map);
  mapState.marker.on('dragend', () => {
    const p = mapState.marker.getLatLng();
    setCoordInputs(p.lat, p.lng);
  });

  // clic en el mapa = mover el equipo ahi
  mapState.map.on('click', (e) => setCoordInputs(e.latlng.lat, e.latlng.lng));
  mapState.map.on('zoomend', updateZoomLabel);

  // Leaflet cachea el tamaño del contenedor al crearse. La pestaña arranca
  // oculta y el layout se asienta después, así que en vez de adivinar con
  // setTimeout observamos el contenedor y recalculamos cuando cambia de veras.
  if (typeof ResizeObserver !== 'undefined') {
    mapState.observer = new ResizeObserver(() => {
      if (mapState.map) mapState.map.invalidateSize({ animate: false });
    });
    mapState.observer.observe(host);
  }
  window.addEventListener('resize', () => {
    if (mapState.map) mapState.map.invalidateSize({ animate: false });
  });

  mapState.ready = true;
  updateZoomLabel();
  console.log('[MAPA] Leaflet inicializado en ' + lat + ', ' + lon);
}

function updateZoomLabel() {
  if (!mapState.map) return;
  document.getElementById('mapZoom').textContent = 'Zoom: ' + mapState.map.getZoom();
}

/** Escribe en los inputs y propaga (sin volver a mover el mapa). */
function setCoordInputs(lat, lon) {
  mapState.syncing = true;
  document.getElementById('latInput').value = lat.toFixed(6);
  document.getElementById('lonInput').value = lon.toFixed(6);
  updateLocationInfo();
  mapState.syncing = false;
}

/** Mueve mapa y marcador a unas coordenadas. */
function setMapView(lat, lon, zoom) {
  if (!mapState.ready) return;
  mapState.marker.setLatLng([lat, lon]);
  if (!mapState.syncing) {
    mapState.map.setView([lat, lon], zoom || mapState.map.getZoom());
  }
  updateZoomLabel();
}

function retryMapTiles() {
  if (!mapState.ready) { initMap(); return; }
  mapState.tileErrors = 0;
  showMapState(false);
  document.getElementById('mapSource').textContent = 'Cargando mapa…';
  mapState.layer.redraw();
}

/** Leaflet necesita que el contenedor tenga tamaño; la pestaña arranca oculta. */
function refreshMapSize() {
  try {
    if (!mapState.ready) initMap();
    if (!mapState.ready) return;
    // Red de seguridad por si el navegador no soporta ResizeObserver.
    [0, 120, 400].forEach(d => setTimeout(() => {
      if (mapState.map) mapState.map.invalidateSize({ animate: false });
    }, d));
  } catch (err) {
    console.error('[MAPA] refreshMapSize falló: ' + err.message + ' | ' + err.stack);
    showMapState(true, 'Error del mapa', err.message);
  }
}

/* ===== LOCATION ===== */
function updateLocationInfo() {
  const lat = parseFloat(document.getElementById('latInput').value) || 0;
  const lon = parseFloat(document.getElementById('lonInput').value) || 0;
  const latHem = lat >= 0 ? 'Norte' : 'Sur';
  const lonHem = lon >= 0 ? 'Este' : 'Oeste';
  const tz = Math.round(lon / 15);
  const tzStr = tz >= 0 ? `UTC+${tz}` : `UTC${tz}`;
  const region = Math.abs(lat) <= 23.5 ? 'Tropical' : Math.abs(lat) <= 45 ? 'Templada' : 'Polar';
  const irr = Math.abs(lat) <= 23.5 ? '5.0–6.5' : Math.abs(lat) <= 45 ? '3.5–5.0' : '1.0–3.5';
  const hrs = Math.abs(lat) <= 23.5 ? '10–12' : Math.abs(lat) <= 45 ? '8–10' : '4–8';
  const orient = lat >= 0 ? 'Sur (Hemisferio Norte)' : 'Norte (Hemisferio Sur)';

  document.getElementById('locationInfoBox').innerHTML = `
    <strong>Coordenadas:</strong> ${lat.toFixed(6)}°, ${lon.toFixed(6)}°<br>
    <strong>Hemisferio:</strong> ${latHem} / ${lonHem}<br>
    <strong>Zona Horaria:</strong> ${tzStr}<br>
    <strong>Región:</strong> ${region}<br>
    <strong>Irradiancia estimada:</strong> ${irr} kWh/m²/día<br>
    <strong>Horas de sol:</strong> ${hrs} h/día<br>
    <strong>Mejor orientación:</strong> ${orient}
  `;
  setMapView(lat, lon);
}

function searchLocation() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) return;

  const btn = document.querySelector('.search-row .btn') || null;
  if (btn) { btn.disabled = true; btn.textContent = 'Buscando…'; }

  // Nominatim es el geocodificador de OpenStreetMap. Su politica de uso pide
  // identificar la aplicacion y no abusar del servicio: 1 consulta por accion
  // explicita del usuario, nunca en bucle.
  const url = 'https://nominatim.openstreetmap.org/search'
            + '?format=json&limit=1&addressdetails=0'
            + '&q=' + encodeURIComponent(q);

  fetch(url, { headers: { 'Accept': 'application/json' } })
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(res => {
      if (!res || !res.length) {
        showToast(`Sin resultados para "${q}"`);
        return;
      }
      const lat = parseFloat(res[0].lat), lon = parseFloat(res[0].lon);
      document.getElementById('latInput').value = lat.toFixed(6);
      document.getElementById('lonInput').value = lon.toFixed(6);
      updateLocationInfo();
      setMapView(lat, lon, 13);
      showToast(`Ubicación encontrada: ${res[0].display_name.split(',').slice(0, 2).join(',')}`);
    })
    .catch(err => {
      addLog(`[MAPA] Error de búsqueda: ${err.message}`, 'error');
      showToast('No se pudo buscar: revisá la conexión');
    })
    .finally(() => {
      if (btn) { btn.disabled = false; btn.textContent = 'Buscar'; }
    });
}

function applyCoords() {
  const lat = document.getElementById('latInput').value;
  const lon = document.getElementById('lonInput').value;
  showToast(`Coordenadas aplicadas: ${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)}`);
}

function openGoogleMaps() {
  const lat = document.getElementById('latInput').value;
  const lon = document.getElementById('lonInput').value;
  window.open(`https://www.google.com/maps?q=${lat},${lon}&z=15`, '_blank');
}
function openGoogleEarth() {
  const lat = document.getElementById('latInput').value;
  const lon = document.getElementById('lonInput').value;
  window.open(`https://earth.google.com/web/@${lat},${lon},1000a,1000d,35y,0h,45t,0r`, '_blank');
}

/* ===== DIAGNOSTIC ===== */
function initDiagLog() {
  diagLog('[SISTEMA] Módulo de diagnóstico listo', 'info');
  diagLog('[DAVIS USB] Esperando lectura de la estación...', 'warn');
}

function diagLog(msg, type = '') {
  const el = document.getElementById('diagLogConsole');
  const line = document.createElement('span');
  line.className = 'log-line' + (type ? ' ' + type : '');
  const ts = new Date().toLocaleTimeString('es-CO', { hour12: false });
  line.textContent = `[${ts}] ${msg}`;
  el.appendChild(line);
  el.appendChild(document.createElement('br'));
  el.scrollTop = el.scrollHeight;
}

function clearDiagLog() {
  document.getElementById('diagLogConsole').innerHTML = '';
}

function toggleDiagConn() {
  if (bridge) {
    if (!state.diagConnected) {
      const ip = document.getElementById('diagIP').value;
      const port = parseInt(document.getElementById('diagPort').value) || 502;
      bridge.connectModbus(ip, port);
    } else {
      bridge.disconnectModbus();
    }
    return; // UI is driven by the connectionChanged signal
  }
  state.diagConnected = !state.diagConnected;
  const btn = document.getElementById('diagConnBtn');
  const led = document.getElementById('diagLedConn');
  const sensorLed = document.getElementById('diagLedSensor');
  const estado = document.getElementById('diagEstado');

  if (state.diagConnected) {
    btn.textContent = 'Desconectar';
    btn.className = 'btn btn-danger full-width';
    led.className = 'led green';
    sensorLed.className = 'led green';
    estado.textContent = 'Conectado';
    diagLog(`[MODBUS] Conectado a ${document.getElementById('diagIP').value}:${document.getElementById('diagPort').value}`, 'info');
    document.getElementById('connDot').className = 'status-dot green';
  } else {
    btn.textContent = 'Conectar';
    btn.className = 'btn btn-primary full-width';
    led.className = 'led red';
    sensorLed.className = 'led red';
    estado.textContent = 'Desconectado';
    diagLog('[MODBUS] Desconectado', 'warn');
    document.getElementById('connDot').className = 'status-dot red';
  }
}

function updateDiagUI() {
  state.diagUpdateCount++;
  const ts = new Date().toLocaleTimeString('es-CO', { hour12: false });
  document.getElementById('diagRad').textContent = state.irradiance.toFixed(2) + ' W/m²';
  document.getElementById('diagQuality').textContent = state.irradiance > 0 ? 'Good' : 'Bad';
  document.getElementById('diagTimestamp').textContent = ts;
  document.getElementById('diagUpdateCount').textContent = state.diagUpdateCount;
}

function updateDavisDiagnostic() {
  const status = state.davisStatus || {};
  const data = state.davisWeather || status.last_reading || {};
  const transport = status.transport || document.getElementById('davisTransport')?.value || 'serial';
  const isSerial = transport === 'serial';
  setText('diagDavisTransport', isSerial ? 'USB serial' : 'IP');
  setText('diagDavisPort', isSerial ? (status.serial_port || '--') : `${status.ip_host || '--'}:${status.ip_port || '--'}`);
  setText('diagDavisState', state.davisConnected ? 'Conectada' : 'Desconectada');
  setText('diagDavisQuality', state.davisConnected && data.solar_radiation_wm2 !== undefined ? 'Lectura válida' : 'Sin lectura válida');
  setText('diagDavisLast', state.davisLastRead ? state.davisLastRead.toLocaleTimeString('es-CO', { hour12: false }) : '--');
  setText('diagDavisCount', String(status.read_count || state.groupHistory.length || 0));
  setText('diagDavisError', status.last_error || '--');
  setText('diagDavisSolar', fmtValue(data.solar_radiation_wm2, 0) + ' W/m²');
  const led = document.getElementById('diagDavisLed');
  if (led) led.className = 'led ' + (state.davisConnected ? 'green' : 'red');
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function runDiagnostic() {
  diagLog('[DIAG] Iniciando diagnóstico automático...', 'info');
  setTimeout(() => {
    refreshDavisStatus();
    const ok = state.davisConnected && !!state.davisWeather;
    const led = document.getElementById('diagDavisLed');
    if (led) led.className = 'led ' + (ok ? 'green' : 'yellow');
    diagLog(`[DIAG] Davis USB: ${state.davisConnected ? 'conectada' : 'sin conexión'}`, state.davisConnected ? 'info' : 'warn');
    diagLog(`[DIAG] Lecturas Davis: ${state.groupHistory.length}`, state.groupHistory.length ? 'info' : 'warn');
    diagLog('[DIAG] Diagnóstico completado', 'info');
    showToast('Diagnóstico completado');
  }, 800);
}

function diagReadDavis() {
  if (!state.davisConnected) {
    showToast('Davis USB no conectada', 'error');
    diagLog('[DAVIS USB] Lectura cancelada: estación no conectada', 'error');
    return;
  }
  if (bridge && bridge.readDavisOnce) {
    bridge.readDavisOnce();
    diagLog('[DAVIS USB] Lectura LOOP solicitada', 'info');
  }
}

function diagReadRad() {
  if (!state.diagConnected) { showToast('No conectado', 'error'); return; }
  if (bridge) { bridge.readRadiation(); diagLog('[MODBUS] Lectura solicitada', 'info'); return; }
  diagLog('[MODBUS] Leyendo registro de radiación...', 'info');
  setTimeout(() => {
    diagLog(`[MODBUS] Radiación: ${state.irradiance.toFixed(2)} W/m²`, 'info');
    updateDiagUI();
  }, 300);
}

function toggleAutoRead() {
  state.diagAutoRead = document.getElementById('autoReadCheck').checked;
  if (bridge) bridge.setAutoRead(state.diagAutoRead);
  diagLog(`Lectura automática ${state.diagAutoRead ? 'activada' : 'desactivada'}`, 'info');
}

function startModbusTest() {
  document.getElementById('diagTestBtn').disabled = true;
  document.getElementById('diagStopBtn').disabled = false;
  diagLog('[TEST] Iniciando prueba Modbus...', 'info');
  if (bridge) { bridge.modbusTest(); return; }
  if (state.diagConnected) {
    diagLog('[TEST] Paquete enviado y recibido correctamente', 'info');
  } else {
    diagLog('[TEST] Error: No conectado', 'error');
  }
}

function stopModbusTest() {
  document.getElementById('diagTestBtn').disabled = false;
  document.getElementById('diagStopBtn').disabled = true;
  diagLog('[TEST] Prueba Modbus detenida', 'warn');
}

function diagExitSafeState() {
  if (bridge) bridge.recoverSafeState();
  document.getElementById('diagSafeStateLed').className = 'led green';
  document.getElementById('diagSafeStateText').textContent = 'Estado: Normal';
  document.getElementById('diagRecoveryBtn').classList.add('hidden');
  diagLog('[SISTEMA] Saliendo del MODO SEGURO', 'info');
  showToast('Sistema recuperado');
}

/* ===== DOCUMENTATION ===== */
const DOC_CONTENT = `
<h1>Prácticas del Banco de Pruebas de Radiación Solar SCADA</h1>
<h2>Práctica #1 – Evaluación del comportamiento de la irradiancia</h2>
<p><strong>Alcance:</strong> Explorar el impacto de factores reales del entorno en la medición de radiación solar.</p>
<p><strong>Objetivo:</strong> Identificar variaciones en la irradiancia captada bajo diferentes condiciones ambientales y horarios.</p>
<h3>Procedimiento de laboratorio</h3>
<ol>
  <li>Encender el sistema y verificar la conexión de lectura.</li>
  <li>Medir irradiancia en zona despejada, parcialmente sombreada y cubierta.</li>
  <li>Repetir el proceso en la mañana, mediodía y tarde.</li>
  <li>Registrar hora, condiciones ambientales y lecturas.</li>
</ol>
<hr>
<h2>Práctica #2 – Visualización de datos en tiempo real</h2>
<p><strong>Objetivo:</strong> Familiarizar al estudiante con Nexo Solar para análisis e interpretación de datos meteorológicos.</p>
<h3>Procedimiento de laboratorio</h3>
<ol>
  <li>Conectar el datalogger Davis por USB.</li>
  <li>Verificar el puerto serial configurado.</li>
  <li>Abrir Nexo Solar y presionar "Conectar".</li>
  <li>Visualizar mediciones en tiempo real y revisar el diagnóstico Davis USB.</li>
</ol>
<hr>
<h2>Práctica #3 – Ubicación del equipo</h2>
<p><strong>Objetivo:</strong> Configurar las coordenadas geográficas del punto de medición.</p>
<h3>Procedimiento de laboratorio</h3>
<ol>
  <li>Buscar el sitio de instalación en el mapa.</li>
  <li>Verificar latitud y longitud.</li>
  <li>Guardar las coordenadas del equipo.</li>
  <li>Registrar observaciones del entorno de medición.</li>
</ol>
<hr>
<h2>Práctica #4 – Variables meteorológicas Davis</h2>
<p><strong>Objetivo:</strong> Relacionar radiación solar, temperatura, humedad, presión, viento, lluvia e índice UV.</p>
<h3>Procedimiento de laboratorio</h3>
<ol>
  <li>Conectar la estación meteorológica.</li>
  <li>Verificar que las unidades se muestren en el sistema internacional.</li>
  <li>Comparar cambios de radiación con humedad, nubosidad y viento.</li>
  <li>Registrar los valores en una tabla de laboratorio.</li>
</ol>
<hr>
<h2>Práctica #5 – Análisis de datos desde la base de datos</h2>
<p><strong>Objetivo:</strong> Extraer y analizar datos registrados en la base de datos SQLite.</p>
<h3>Procedimiento de laboratorio</h3>
<ol>
  <li>Abrir software de SQLite y cargar base de datos.</li>
  <li>Navegar a la tabla configurada para la práctica.</li>
  <li>Exportar datos como archivo <code>.csv</code>.</li>
  <li>Abrir en Excel o Google Sheets y calcular estadísticas.</li>
</ol>
`;

function loadDoc() {
  document.getElementById('docViewer').innerHTML = DOC_CONTENT;
}

function reloadDoc() {
  loadDoc();
  showToast('Documentación recargada');
}

function toggleDocView() {
  const btn = document.getElementById('docToggleBtn');
  const viewer = document.getElementById('docViewer');
  if (state.docMode === 'html') {
    viewer.innerHTML = '';
    const pre = document.createElement('pre');
    pre.style.cssText = 'font-family:Cascadia Code,Consolas,monospace;font-size:12px;color:#8b949e;white-space:pre-wrap;';
    pre.textContent = DOC_CONTENT.replace(/<[^>]+>/g, '').replace(/\n{3,}/g, '\n\n').trim();
    viewer.appendChild(pre);
    btn.textContent = '🌐 Vista HTML';
    state.docMode = 'markdown';
  } else {
    loadDoc();
    btn.textContent = '📝 Vista Código';
    state.docMode = 'html';
  }
}

/* ===== GROUP CHARTS ===== */
const groupCharts = {
  solar: null,
  temp: null,
  humidity: null,
  wind: null,
  rain: null,
};

function initGroupCharts() {
  groupCharts.solar = document.getElementById('groupChartSolar')?.getContext('2d') || null;
  groupCharts.temp = document.getElementById('groupChartTemp')?.getContext('2d') || null;
  groupCharts.humidity = document.getElementById('groupChartHumidity')?.getContext('2d') || null;
  groupCharts.wind = document.getElementById('groupChartWind')?.getContext('2d') || null;
  groupCharts.rain = document.getElementById('groupChartRain')?.getContext('2d') || null;
  drawGroupCharts();
}

function pushGroupHistory(data) {
  const row = {
    t: new Date(),
    solar: data.solar_radiation_wm2,
    uv: data.uv_index,
    tempOut: data.temp_out_c,
    tempIn: data.temp_in_c,
    humidityOut: data.humidity_out,
    humidityIn: data.humidity_in,
    pressure: data.pressure_hpa,
    wind: data.wind_speed_ms,
    windAvg: data.wind_speed_avg_ms,
    windDir: data.wind_dir_deg,
    rainRate: data.rain_rate_mm,
    rainDay: data.rain_day_mm,
    rainMonth: data.rain_month_mm,
    rainYear: data.rain_year_mm,
    siteEnergy: state.siteEnergyKwhM2,
    panelEnergy: state.siteEnergyKwhM2 * state.panelAreaM2 * state.panelEfficiency,
  };
  state.groupHistory.push(row);
  trimArrayStart(state.groupHistory, state.maxGroupHistory);
}

function drawGroupCharts() {
  const rows = getVisibleGroupRows();
  const solarRows = buildSolarEnergyRows(rows);
  drawMultiLineChart('groupChartSolar', groupCharts.solar, [
    { key: 'solar', label: 'Radiación W/m²', color: '#ffb703' },
    { key: 'uv', label: 'UV x100', color: '#2563eb', scale: 100 },
    { key: 'siteEnergy', label: 'Energía kWh/m² x10000', color: '#16a34a', scale: 10000 },
    { key: 'panelEnergy', label: 'Panel kWh x10000', color: '#0f766e', scale: 10000 },
  ], {
    chartId: 'solar',
    rows: solarRows,
    includeZero: true,
    emptyMessage: 'Esperando datos solares Davis',
  });
  drawMultiLineChart('groupChartTemp', groupCharts.temp, [
    { key: 'tempOut', label: 'Exterior °C', color: '#ef4444' },
    { key: 'tempIn', label: 'Interior °C', color: '#16a34a' },
  ], {
    chartId: 'temp',
    rows,
    includeZero: false,
    emptyMessage: 'Esperando temperaturas Davis',
  });
  drawMultiLineChart('groupChartHumidity', groupCharts.humidity, [
    { key: 'humidityOut', label: 'Humedad ext %', color: '#0891b2' },
    { key: 'humidityIn', label: 'Humedad int %', color: '#22c55e' },
    { key: 'pressure', label: 'Presión hPa - 950', color: '#7c3aed', offset: 950 },
  ], {
    chartId: 'humidity',
    rows,
    includeZero: true,
    emptyMessage: 'Esperando humedad y presión',
  });
  drawMultiLineChart('groupChartWind', groupCharts.wind, [
    { key: 'wind', label: 'Viento m/s', color: '#0f766e' },
    { key: 'windAvg', label: 'Promedio m/s', color: '#84cc16' },
    { key: 'windDir', label: 'Dirección /12', color: '#f97316', scale: 1 / 12 },
  ], {
    chartId: 'wind',
    rows,
    includeZero: true,
    emptyMessage: 'Esperando datos de viento',
  });
  drawMultiLineChart('groupChartRain', groupCharts.rain, [
    { key: 'rainRate', label: 'Tasa mm', color: '#2563eb' },
    { key: 'rainDay', label: 'Día mm', color: '#06b6d4' },
    { key: 'rainMonth', label: 'Mes mm /2', color: '#16a34a', scale: 0.5 },
    { key: 'rainYear', label: 'Año mm /20', color: '#f59e0b', scale: 0.05 },
  ], {
    chartId: 'rain',
    rows,
    includeZero: true,
    emptyMessage: 'Esperando datos de lluvia',
  });
}

function setGraphRange(hours, btn) {
  state.graphRangeHours = hours;
  document.querySelectorAll('#tab-graficas .range-chip').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadDavisHistory();
  drawGroupCharts();
}

function zoomGraph(chartId, direction) {
  if (!state.graphZoom[chartId]) return;
  state.graphZoom[chartId] = clampZoom(state.graphZoom[chartId] + direction * 0.25);
  updateGraphZoomLabel(chartId);
  drawGroupCharts();
}

function resetGraphZoom(chartId) {
  if (!state.graphZoom[chartId]) return;
  state.graphZoom[chartId] = 1;
  updateGraphZoomLabel(chartId);
  drawGroupCharts();
}

function updateGraphZoomLabel(chartId) {
  const labelIds = {
    solar: 'graphZoomLabelSolar',
    temp: 'graphZoomLabelTemp',
    humidity: 'graphZoomLabelHumidity',
    wind: 'graphZoomLabelWind',
    rain: 'graphZoomLabelRain',
  };
  setText(labelIds[chartId], `${Math.round(state.graphZoom[chartId] * 100)}%`);
}

function getVisibleGroupRows() {
  if (state.graphRangeHours === 0) return state.groupHistory.slice();
  const since = Date.now() - state.graphRangeHours * 3600000;
  const rows = state.groupHistory.filter(row => row.t && row.t.getTime() >= since);
  return rows.length ? rows : [];
}

function drawMultiLineChart(canvasId, ctx, series, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !ctx) return;
  const rows = options.rows || state.groupHistory;
  const zoom = state.graphZoom[options.chartId] || 1;
  const size = prepareScrollableCanvas(canvas, zoom, rows.length);
  const width = size.width;
  const height = parseInt(canvas.getAttribute('height'), 10) || 220;
  const pad = { top: 24, right: 18, bottom: 28, left: 48 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const axis = getChartAxis(rows, series, options.includeZero !== false);

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = '#d9e2d0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * chartH;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillStyle = '#5d6757';
    ctx.font = '10px Segoe UI';
    ctx.textAlign = 'right';
    ctx.fillText(formatAxisValue(axis.max - (i / 4) * (axis.max - axis.min)), pad.left - 6, y + 3);
  }

  if (!rows.length) {
    ctx.fillStyle = '#697463';
    ctx.font = '12px Segoe UI';
    ctx.textAlign = 'center';
    ctx.fillText(options.emptyMessage || 'Esperando lecturas', Math.min(width / 2, size.viewportWidth / 2), height / 2);
    return;
  }

  series.forEach((item) => {
    ctx.beginPath();
    let hasPoint = false;
    rows.forEach((row, i) => {
      const value = transformSeriesValue(row[item.key], item);
      if (value === null) return;
      const x = rows.length === 1 ? pad.left + chartW / 2 : pad.left + (i / (rows.length - 1)) * chartW;
      const y = pad.top + (1 - (value - axis.min) / (axis.max - axis.min)) * chartH;
      hasPoint ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      if (rows.length === 1) {
        ctx.arc(x, y, 3, 0, Math.PI * 2);
      }
      hasPoint = true;
    });
    if (!hasPoint) return;
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  let legendX = pad.left;
  series.forEach((item) => {
    ctx.fillStyle = item.color;
    ctx.fillRect(legendX, 6, 14, 4);
    ctx.fillStyle = '#42503b';
    ctx.font = '10px Segoe UI';
    ctx.textAlign = 'left';
    ctx.fillText(item.label, legendX + 18, 10);
    legendX += Math.min(160, item.label.length * 6 + 36);
  });
}

function buildSolarEnergyRows(rows) {
  let siteEnergy = 0;
  let lastTime = null;
  return rows.map((row) => {
    const copy = { ...row };
    const solar = normalizeIrradiance(row.solar);
    const currentTime = row.t instanceof Date ? row.t.getTime() : null;
    if (solar !== null && lastTime !== null && currentTime !== null) {
      const elapsedHours = Math.max(0, Math.min((currentTime - lastTime) / 3600000, 1 / 12));
      siteEnergy += solar * elapsedHours / 1000;
    }
    if (currentTime !== null) lastTime = currentTime;
    copy.siteEnergy = Number.isFinite(row.siteEnergy) ? row.siteEnergy : siteEnergy;
    copy.panelEnergy = Number.isFinite(row.panelEnergy)
      ? row.panelEnergy
      : copy.siteEnergy * state.panelAreaM2 * state.panelEfficiency;
    return copy;
  });
}

function getChartAxis(rows, series, includeZero) {
  const values = [];
  rows.forEach(row => {
    series.forEach(item => {
      const value = transformSeriesValue(row[item.key], item);
      if (value !== null) values.push(value);
    });
  });

  if (!values.length) return { min: 0, max: 1 };
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (includeZero) min = Math.min(0, min);
  if (min === max) {
    const pad = Math.max(1, Math.abs(max) * 0.1);
    min -= includeZero ? 0 : pad;
    max += pad;
  } else {
    const pad = (max - min) * 0.12;
    min = includeZero ? Math.min(0, min) : min - pad;
    max += pad;
  }
  return { min, max };
}

function transformSeriesValue(raw, item) {
  const value = Number(raw);
  if (!Number.isFinite(value)) return null;
  const shifted = value - (item.offset || 0);
  return shifted * (item.scale || 1);
}

function formatAxisValue(value) {
  if (Math.abs(value) >= 100) return Math.round(value).toString();
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

/* ===== RESIZE ===== */
window.addEventListener('resize', () => {
  drawChart();
  drawGroupCharts();
});

/* ============================================================
   ANÁLISIS DE DATOS
   ============================================================ */

let anaData = [];
let anaFiltered = [];
let anaPage = 0;
const ANA_PAGE_SIZE = 20;
let anaSortKey = 'id';
let anaSortAsc = true;
let anaView = 'day';
let anaKind = 'davis';

/* ----- Canvases ----- */
let anaHistCtx, anaDistCtx, anaHeatCtx, anaHourCtx;

function initAnalysisCanvases() {
  anaHistCtx = document.getElementById('anaHistChart').getContext('2d');
  anaDistCtx = document.getElementById('anaDistChart').getContext('2d');
  anaHeatCtx = document.getElementById('anaHeatmap').getContext('2d');
  anaHourCtx = document.getElementById('anaHourlyChart').getContext('2d');
}

/* ----- Carga principal ----- */
/** El filtro de fechas solo se aplica si el usuario lo eligió. Arrancar con
 *  un rango fijo escondía los datos reales, que caían fuera de ese rango. */
let anaDatesTouched = false;
function markDatesTouched() { anaDatesTouched = true; }

/** Llena el selector de Fuente con las tablas reales de la base. */
function populateTableSelect() {
  const sel = document.getElementById('anaTableSelect');
  if (!sel || !bridge) return;
  refreshActiveDatabase();
  bridge.listTables(function (tables) {
    if (!tables || !tables.length) {
      sel.innerHTML = '<option value="">Sin tablas en la base activa</option>';
      return;
    }
    sel.innerHTML = '';
    tables.forEach(t => {
      const o = document.createElement('option');
      o.value = t.name;
      o.dataset.kind = t.kind || 'other';
      const label = t.kind === 'davis' ? 'Davis' : t.kind === 'legacy_irradiance' ? 'Heredada' : 'Otro esquema';
      o.textContent = `${label}: ${t.name} (${t.count.toLocaleString()})`;
      if (state.activeDatabase.analysis_table === t.name || state.activeDatabase.analysisTable === t.name) {
        o.selected = true;
      }
      sel.appendChild(o);
    });
    sel.onchange = () => {
      anaDatesTouched = false;   // cada tabla cubre su propio período
      bridge.setAnalysisTable(sel.value, () => loadAnalysisData());
    };
  });
}

function loadAnalysisData() {
  const btn = document.querySelector('[onclick="loadAnalysisData()"]');
  const icon = document.getElementById('loadBtnIcon');
  icon.textContent = '⟳';
  btn.disabled = true;

  const finish = (rows, fromBackend, notice) => {
    anaData = rows;
    // Reflejar en los inputs el rango que de verdad cubre la tabla.
    if (!anaDatesTouched && rows.length) {
      document.getElementById('anaDateFrom').value = rows[0].fecha;
      document.getElementById('anaDateTo').value = rows[rows.length - 1].fecha;
    } else if (!anaDatesTouched) {
      document.getElementById('anaDateFrom').value = '';
      document.getElementById('anaDateTo').value = '';
    }
    applyDateFilter();
    icon.textContent = '⬇';
    btn.disabled = false;
    setAnalysisSource(fromBackend, notice);
    showToast(`${anaData.length.toLocaleString()} registros cargados${fromBackend ? ' (base de datos)' : ''}`);
  };

  if (bridge) {
    const from = anaDatesTouched ? (document.getElementById('anaDateFrom').value || '') : '';
    const to = anaDatesTouched ? (document.getElementById('anaDateTo').value || '') : '';
    bridge.loadAnalysis(from, to, function (res) {
      // El bridge distingue "consulta falló" de "tabla vacía": son cosas
      // distintas y el usuario tiene que poder diferenciarlas.
      const rows = (res && res.rows) || [];
      anaKind = (res && res.kind) || 'unknown';
      if (rows.length) {
        finish(rows, true, '');
        return;
      }
      if (res && res.ok === false) {
        addLog(`[Análisis] Error al leer la base: ${res.error}`, 'error');
        finish([], false,
          `No se pudo leer la tabla «${res.table}»: ${res.error}`);
      } else {
        addLog('[Análisis] La tabla está vacía; esperando registros reales de la estación', 'info');
        finish([], true,
          `La tabla «${(res && res.table) || '—'}» no tiene registros todavía.`);
      }
    });
    return;
  }

  setTimeout(() => finish([], false,
    'Vista abierta fuera de la aplicación, sin acceso a la base de datos.'), 200);
}

/** Aviso permanente para estados vacios o errores de lectura. */
function setAnalysisSource(fromBackend, notice) {
  const el = document.getElementById('anaSourceBanner');
  if (!el) return;
  if (fromBackend && !notice) { el.setAttribute('hidden', ''); return; }
  document.getElementById('anaSourceDetail').textContent = notice || '';
  el.removeAttribute('hidden');
}

function applyDateFilter() {
  if (!anaData.length) {
    anaFiltered = [];
    anaPage = 0;
    renderAll();
    return;
  }
  const from = document.getElementById('anaDateFrom').value;
  const to   = document.getElementById('anaDateTo').value;
  anaFiltered = anaData.filter(r => {
    const afterStart = !from || r.fecha >= from;
    const beforeEnd = !to || r.fecha <= to;
    return afterStart && beforeEnd;
  });
  anaPage = 0;
  renderAll();
}

function renderAll() {
  updateKPIs();
  drawHistChart();
  drawDistChart();
  drawHeatmap();
  drawHourlyChart();
  renderTable();
}

function drawEmptyAnalysisCanvas(canvasId, ctx, message) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !ctx) return;
  canvas.width = canvas.parentElement.clientWidth || 600;
  const height = parseInt(canvas.getAttribute('height'), 10) || 220;
  ctx.clearRect(0, 0, canvas.width, height);
  ctx.fillStyle = '#697463';
  ctx.font = '12px Segoe UI';
  ctx.textAlign = 'center';
  ctx.fillText(message, canvas.width / 2, height / 2);
}

/* ----- KPIs ----- */
/** Intervalo de muestreo en minutos, estimado con la mediana de los saltos
 *  entre registros consecutivos del mismo día. */
function samplingMinutes(rows) {
  if (rows.length < 2) return 1;
  const secs = (r) => {
    const p = String(r.hora).split(':').map(Number);
    return (p[0] || 0) * 3600 + (p[1] || 0) * 60 + (p[2] || 0);
  };
  const deltas = [];
  for (let i = 1; i < rows.length && deltas.length < 500; i++) {
    if (rows[i].fecha !== rows[i - 1].fecha) continue;
    const d = secs(rows[i]) - secs(rows[i - 1]);
    if (d > 0) deltas.push(d);
  }
  if (!deltas.length) return 1;
  deltas.sort((a, b) => a - b);
  return deltas[Math.floor(deltas.length / 2)] / 60;
}

function updateKPIs() {
  if (!anaFiltered.length) {
    document.getElementById('kpiMax').textContent = '-- W/m²';
    document.getElementById('kpiMaxDate').textContent = '--';
    document.getElementById('kpiAvg').textContent = '-- W/m²';
    document.getElementById('kpiAvgSub').textContent = 'sin muestras';
    document.getElementById('kpiEnergy').textContent = '-- kWh/m²';
    document.getElementById('kpiStd').textContent = '-- W/m²';
    document.getElementById('kpiCount').textContent = '0';
    document.getElementById('kpiCountSub').textContent = 'en espera de registros';
    return;
  }
  const vals = anaFiltered.map(r => r.irradiancia);
  const max  = Math.max(...vals);
  const avg  = vals.reduce((a,b) => a+b, 0) / vals.length;
  // El intervalo de muestreo no es fijo; se deduce de los propios datos para
  // estimar energia sin asumir una frecuencia de adquisicion.
  const energy = (avg * anaFiltered.length * (samplingMinutes(anaFiltered)/60) / 1000).toFixed(1);
  const std  = Math.sqrt(vals.reduce((a,b) => a + (b-avg)**2, 0) / vals.length);
  const maxRow = anaFiltered.find(r => r.irradiancia === max);

  document.getElementById('kpiMax').textContent    = max.toFixed(1) + ' W/m²';
  document.getElementById('kpiMaxDate').textContent = maxRow ? `${maxRow.fecha} · ${maxRow.hora}` : '—';
  document.getElementById('kpiAvg').textContent    = avg.toFixed(1) + ' W/m²';
  document.getElementById('kpiAvgSub').textContent = `${anaFiltered.length.toLocaleString()} muestras`;
  // parseInt truncaba a 0 los valores menores a 1 kWh/m², que es justo el
  // orden de magnitud de una campaña de pocas horas.
  const energyNum = parseFloat(energy);
  document.getElementById('kpiEnergy').textContent =
    (energyNum < 10 ? energyNum.toFixed(2) : Math.round(energyNum).toLocaleString()) + ' kWh/m²';
  document.getElementById('kpiStd').textContent    = '±' + std.toFixed(0) + ' W/m²';
  document.getElementById('kpiCount').textContent  = anaFiltered.length.toLocaleString();
  document.getElementById('kpiCountSub').textContent = `${anaFiltered[0]?.fecha} → ${anaFiltered[anaFiltered.length-1]?.fecha}`;
}

/* ----- Vista histórica ----- */
function setAnaView(v, btn) {
  anaView = v;
  document.querySelectorAll('#tab-datos .chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  drawHistChart();
}

function drawHistChart() {
  if (!anaFiltered.length) {
    drawEmptyAnalysisCanvas('anaHistChart', anaHistCtx, 'Sin registros para graficar');
    return;
  }
  const canvas = document.getElementById('anaHistChart');
  canvas.width = canvas.parentElement.clientWidth || 700;
  const c = anaHistCtx;
  const W = canvas.width, H = 220;
  c.clearRect(0, 0, W, H);

  // Aggregate by view
  const grouped = {};
  anaFiltered.forEach(r => {
    let key;
    if (anaView === 'day') {
      key = r.fecha + ' ' + r.hora.slice(0,2) + ':00';
    } else if (anaView === 'week') {
      const d = new Date(r.fecha);
      const week = Math.floor((d - new Date('2025-01-01')) / (7*86400000));
      key = `Sem ${week + 1}`;
    } else {
      key = r.fecha.slice(0, 7);
    }
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(r.irradiancia);
  });

  const labels = Object.keys(grouped).slice(-60);
  const avgs   = labels.map(k => grouped[k].reduce((a,b)=>a+b,0)/grouped[k].length);
  const maxs   = labels.map(k => Math.max(...grouped[k]));

  const pad = { top: 20, right: 16, bottom: 36, left: 52 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;
  const maxY = 2000;

  // Grid
  c.strokeStyle = '#21262d'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i/4)*iH;
    c.beginPath(); c.moveTo(pad.left, y); c.lineTo(W-pad.right, y); c.stroke();
    c.fillStyle = '#6e7681'; c.font = '10px Segoe UI'; c.textAlign = 'right';
    c.fillText(Math.round(maxY - (i/4)*maxY), pad.left-6, y+4);
  }

  if (labels.length < 2) return;

  // Max area (subtle)
  c.beginPath();
  maxs.forEach((v,i) => {
    const x = pad.left + (i/(labels.length-1))*iW;
    const y = pad.top + (1 - v/maxY)*iH;
    i===0 ? c.moveTo(x,y) : c.lineTo(x,y);
  });
  c.strokeStyle = 'rgba(240,136,62,0.3)'; c.lineWidth = 1; c.stroke();

  // Avg line + fill
  const grad = c.createLinearGradient(0, pad.top, 0, H-pad.bottom);
  grad.addColorStop(0, 'rgba(88,166,255,0.25)');
  grad.addColorStop(1, 'rgba(88,166,255,0)');

  c.beginPath();
  avgs.forEach((v,i) => {
    const x = pad.left + (i/(labels.length-1))*iW;
    const y = pad.top + (1 - v/maxY)*iH;
    i===0 ? c.moveTo(x,y) : c.lineTo(x,y);
  });
  c.strokeStyle = '#58a6ff'; c.lineWidth = 2; c.stroke();
  c.lineTo(pad.left+iW, H-pad.bottom);
  c.lineTo(pad.left, H-pad.bottom);
  c.closePath(); c.fillStyle = grad; c.fill();

  // X labels (sparse)
  c.fillStyle = '#6e7681'; c.font = '9px Segoe UI'; c.textAlign = 'center';
  const step = Math.max(1, Math.floor(labels.length / 8));
  labels.forEach((l, i) => {
    if (i % step !== 0) return;
    const x = pad.left + (i/(labels.length-1))*iW;
    c.fillText(l.slice(-5), x, H-pad.bottom+14);
  });

  // Legend
  c.fillStyle = '#58a6ff'; c.fillRect(pad.left, 4, 12, 4);
  c.fillStyle = '#8b949e'; c.font = '10px Segoe UI'; c.textAlign = 'left';
  c.fillText('Promedio', pad.left+16, 10);
  c.fillStyle = 'rgba(240,136,62,0.6)'; c.fillRect(pad.left+90, 4, 12, 4);
  c.fillStyle = '#8b949e'; c.fillText('Máximo', pad.left+106, 10);
}

/* ----- Distribución por rangos ----- */
function drawDistChart() {
  if (!anaFiltered.length) {
    drawEmptyAnalysisCanvas('anaDistChart', anaDistCtx, 'Sin distribución todavía');
    return;
  }
  const canvas = document.getElementById('anaDistChart');
  canvas.width = canvas.parentElement.clientWidth || 380;
  const c = anaDistCtx;
  const W = canvas.width, H = 220;
  c.clearRect(0, 0, W, H);

  const bins = [
    { label: '0–200',    min: 0,    max: 200,  color: '#30363d' },
    { label: '200–400',  min: 200,  max: 400,  color: '#1a3a5c' },
    { label: '400–600',  min: 400,  max: 600,  color: '#1f6feb' },
    { label: '600–800',  min: 600,  max: 800,  color: '#3fb950' },
    { label: '800–1000', min: 800,  max: 1000, color: '#a8d672' },
    { label: '1000–1200',min: 1000, max: 1200, color: '#d29922' },
    { label: '1200–1500',min: 1200, max: 1500, color: '#f0883e' },
    { label: '1500+',    min: 1500, max: 9999, color: '#f78166' },
  ];

  bins.forEach(b => {
    b.count = anaFiltered.filter(r => r.irradiancia >= b.min && r.irradiancia < b.max).length;
  });

  const maxCount = Math.max(...bins.map(b => b.count));
  const pad = { top: 16, right: 16, bottom: 60, left: 52 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;
  const barW = iW / bins.length;

  // Grid
  c.strokeStyle = '#21262d'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i/4)*iH;
    c.beginPath(); c.moveTo(pad.left, y); c.lineTo(W-pad.right, y); c.stroke();
    c.fillStyle = '#6e7681'; c.font = '10px Segoe UI'; c.textAlign = 'right';
    c.fillText(Math.round(maxCount - (i/4)*maxCount), pad.left-4, y+4);
  }

  bins.forEach((b, i) => {
    const x = pad.left + i * barW + barW * 0.1;
    const bw = barW * 0.8;
    const bh = maxCount > 0 ? (b.count / maxCount) * iH : 0;
    const y = pad.top + iH - bh;

    // Bar with gradient
    const grad = c.createLinearGradient(0, y, 0, y+bh);
    grad.addColorStop(0, b.color);
    grad.addColorStop(1, b.color + '66');
    c.fillStyle = grad;
    c.beginPath();
    c.roundRect(x, y, bw, bh, [3, 3, 0, 0]);
    c.fill();

    // Count label on top
    if (b.count > 0) {
      c.fillStyle = '#8b949e'; c.font = '9px Segoe UI'; c.textAlign = 'center';
      c.fillText(b.count > 999 ? (b.count/1000).toFixed(1)+'k' : b.count, x+bw/2, y-4);
    }

    // X label
    c.fillStyle = '#6e7681'; c.font = '9px Segoe UI'; c.textAlign = 'center';
    c.save();
    c.translate(x+bw/2, H-pad.bottom+8);
    c.rotate(-Math.PI/4);
    c.fillText(b.label, 0, 0);
    c.restore();
  });

  // Y axis title
  c.save();
  c.translate(12, H/2);
  c.rotate(-Math.PI/2);
  c.fillStyle = '#6e7681'; c.font = '10px Segoe UI'; c.textAlign = 'center';
  c.fillText('Frecuencia', 0, 0);
  c.restore();
}

/* ----- Heatmap hora × día de semana ----- */
function drawHeatmap() {
  if (!anaFiltered.length) {
    drawEmptyAnalysisCanvas('anaHeatmap', anaHeatCtx, 'Sin datos por hora');
    return;
  }
  const canvas = document.getElementById('anaHeatmap');
  canvas.width = canvas.parentElement.clientWidth || 700;
  const c = anaHeatCtx;
  const W = canvas.width, H = 200;
  c.clearRect(0, 0, W, H);

  const days  = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
  const hours = Array.from({length:13}, (_,i) => i+6); // 6..18

  // Build grid: [dayOfWeek][hour] = avg irradiance
  const grid = Array.from({length:7}, () => Array(13).fill(null).map(()=>({sum:0,cnt:0})));
  anaFiltered.forEach(r => {
    const d = new Date(r.fecha).getDay();
    const h = parseInt(r.hora.slice(0,2));
    if (h >= 6 && h <= 18) {
      grid[d][h-6].sum += r.irradiancia;
      grid[d][h-6].cnt++;
    }
  });

  const pad = { top: 8, right: 16, bottom: 28, left: 36 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;
  const cellW = iW / hours.length;
  const cellH = iH / days.length;

  // Draw cells
  days.forEach((day, di) => {
    hours.forEach((hr, hi) => {
      const cell = grid[di][hi];
      const avg = cell.cnt > 0 ? cell.sum / cell.cnt : 0;
      const ratio = avg / 1400;
      c.fillStyle = heatColor(ratio);
      c.fillRect(
        pad.left + hi * cellW + 1,
        pad.top  + di * cellH + 1,
        cellW - 2,
        cellH - 2
      );
      // Value text if cell is big enough
      if (cellW > 40 && avg > 0) {
        c.fillStyle = ratio > 0.5 ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.5)';
        c.font = '9px Segoe UI'; c.textAlign = 'center';
        c.fillText(Math.round(avg), pad.left + hi*cellW + cellW/2, pad.top + di*cellH + cellH/2 + 3);
      }
    });
    // Day label
    c.fillStyle = '#8b949e'; c.font = '10px Segoe UI'; c.textAlign = 'right';
    c.fillText(day, pad.left-4, pad.top + di*cellH + cellH/2 + 4);
  });

  // Hour labels
  hours.forEach((hr, hi) => {
    c.fillStyle = '#6e7681'; c.font = '9px Segoe UI'; c.textAlign = 'center';
    c.fillText(hr+'h', pad.left + hi*cellW + cellW/2, H-pad.bottom+12);
  });
}

function heatColor(ratio) {
  // 0 → dark, 0.5 → blue, 0.75 → green, 0.9 → orange, 1 → red
  const stops = [
    [0,    [13,17,23]],
    [0.15, [26,58,92]],
    [0.4,  [31,111,235]],
    [0.65, [63,185,80]],
    [0.82, [210,153,34]],
    [0.93, [240,136,62]],
    [1,    [247,129,102]],
  ];
  for (let i = 1; i < stops.length; i++) {
    if (ratio <= stops[i][0]) {
      const t = (ratio - stops[i-1][0]) / (stops[i][0] - stops[i-1][0]);
      const a = stops[i-1][1], b = stops[i][1];
      const r = Math.round(a[0] + (b[0]-a[0])*t);
      const g = Math.round(a[1] + (b[1]-a[1])*t);
      const bv= Math.round(a[2] + (b[2]-a[2])*t);
      return `rgb(${r},${g},${bv})`;
    }
  }
  return `rgb(247,129,102)`;
}

/* ----- Promedio por hora del día ----- */
function drawHourlyChart() {
  if (!anaFiltered.length) {
    drawEmptyAnalysisCanvas('anaHourlyChart', anaHourCtx, 'Sin promedio horario');
    return;
  }
  const canvas = document.getElementById('anaHourlyChart');
  canvas.width = canvas.parentElement.clientWidth || 380;
  const c = anaHourCtx;
  const W = canvas.width, H = 200;
  c.clearRect(0, 0, W, H);

  const hourly = Array.from({length:13}, (_,i) => ({h:i+6, sum:0, cnt:0, max:0}));
  anaFiltered.forEach(r => {
    const h = parseInt(r.hora.slice(0,2));
    if (h >= 6 && h <= 18) {
      const idx = h - 6;
      hourly[idx].sum += r.irradiancia;
      hourly[idx].cnt++;
      if (r.irradiancia > hourly[idx].max) hourly[idx].max = r.irradiancia;
    }
  });

  const avgs = hourly.map(h => h.cnt > 0 ? h.sum/h.cnt : 0);
  const maxY = 1600;
  const pad = { top: 16, right: 16, bottom: 28, left: 48 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;

  // Grid
  c.strokeStyle = '#21262d'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i/4)*iH;
    c.beginPath(); c.moveTo(pad.left, y); c.lineTo(W-pad.right, y); c.stroke();
    c.fillStyle = '#6e7681'; c.font = '9px Segoe UI'; c.textAlign = 'right';
    c.fillText(Math.round(maxY-(i/4)*maxY), pad.left-4, y+3);
  }

  // Area
  const grad = c.createLinearGradient(0, pad.top, 0, H-pad.bottom);
  grad.addColorStop(0, 'rgba(63,185,80,0.3)');
  grad.addColorStop(1, 'rgba(63,185,80,0)');

  c.beginPath();
  avgs.forEach((v,i) => {
    const x = pad.left + (i/(avgs.length-1))*iW;
    const y = pad.top + (1 - Math.min(v,maxY)/maxY)*iH;
    i===0 ? c.moveTo(x,y) : c.lineTo(x,y);
  });
  c.strokeStyle = '#3fb950'; c.lineWidth = 2; c.stroke();
  c.lineTo(pad.left+iW, H-pad.bottom);
  c.lineTo(pad.left, H-pad.bottom);
  c.closePath(); c.fillStyle = grad; c.fill();

  // Dots + labels
  avgs.forEach((v,i) => {
    const x = pad.left + (i/(avgs.length-1))*iW;
    const y = pad.top + (1 - Math.min(v,maxY)/maxY)*iH;
    c.beginPath(); c.arc(x, y, 3, 0, Math.PI*2);
    c.fillStyle = '#3fb950'; c.fill();
    c.fillStyle = '#6e7681'; c.font = '9px Segoe UI'; c.textAlign = 'center';
    c.fillText((i+6)+'h', x, H-pad.bottom+12);
  });
}

/* ----- Tabla de datos ----- */
let tableData = [];
let tableFiltered = [];

function renderTable() {
  tableData = [...anaFiltered].sort((a,b) => {
    const va = a[anaSortKey], vb = b[anaSortKey];
    if (typeof va === 'number') return anaSortAsc ? va-vb : vb-va;
    return anaSortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  tableFiltered = tableData;
  renderTablePage();
}

function renderTablePage() {
  const tbody = document.getElementById('dataTableBody');
  renderTableHeader();
  const start = anaPage * ANA_PAGE_SIZE;
  const slice = tableFiltered.slice(start, start + ANA_PAGE_SIZE);
  const total = tableFiltered.length;
  const pages = Math.ceil(total / ANA_PAGE_SIZE);

  if (!total) {
    tbody.innerHTML = `<tr><td colspan="${dataColumnCount()}">Sin registros. La tabla empezará a llenarse con lecturas reales de la estación.</td></tr>`;
    document.getElementById('tableCount').textContent = 'mostrando 0 de 0';
    document.getElementById('pageInfo').textContent = 'Página 1 de 1';
    return;
  }

  tbody.innerHTML = slice.map(r => {
    const q = r.irradiancia > 50 ? 'Good' : r.irradiancia > 0 ? 'Warn' : 'Bad';
    const qClass = q === 'Good' ? 'quality-good' : q === 'Warn' ? 'quality-warn' : 'quality-bad';
    if (anaKind === 'davis') {
      const quality = r.quality || q;
      const qualityClass = quality === 'valid' || quality === 'Good' ? 'quality-good' : 'quality-warn';
      return `<tr>
        <td>${r.id}</td>
        <td>${r.fecha}</td>
        <td>${r.hora}</td>
        <td class="irr-val">${numberOrDash(r.solar_radiation_wm2, 1)}</td>
        <td>${numberOrDash(r.uv_index, 1)}</td>
        <td>${numberOrDash(r.temp_out_c, 1)}</td>
        <td>${numberOrDash(r.humidity_out, 0)}</td>
        <td>${numberOrDash(r.pressure_hpa, 1)}</td>
        <td>${numberOrDash(r.wind_speed_ms, 2)}</td>
        <td class="${qualityClass}">${quality}</td>
      </tr>`;
    }
    return `<tr>
      <td>${r.id}</td>
      <td>${r.fecha}</td>
      <td>${r.hora}</td>
      <td class="irr-val">${r.irradiancia.toFixed(2)}</td>
      <td class="${qClass}">${q}</td>
    </tr>`;
  }).join('');

  document.getElementById('tableCount').textContent =
    `mostrando ${Math.min(start+ANA_PAGE_SIZE, total).toLocaleString()} de ${total.toLocaleString()}`;
  document.getElementById('pageInfo').textContent =
    `Página ${anaPage+1} de ${pages || 1}`;
}

function renderTableHeader() {
  const head = document.getElementById('dataTableHead');
  if (!head) return;
  if (anaKind === 'davis') {
    head.innerHTML = `
      <th onclick="sortTable('id')"># <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('fecha')">Fecha <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('hora')">Hora <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('solar_radiation_wm2')">Radiación <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('uv_index')">UV <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('temp_out_c')">Temp. ext. <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('humidity_out')">Humedad <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('pressure_hpa')">Presión <span class="sort-icon">↕</span></th>
      <th onclick="sortTable('wind_speed_ms')">Viento <span class="sort-icon">↕</span></th>
      <th>Calidad</th>`;
    return;
  }
  head.innerHTML = `
    <th onclick="sortTable('id')"># <span class="sort-icon">↕</span></th>
    <th onclick="sortTable('fecha')">Fecha <span class="sort-icon">↕</span></th>
    <th onclick="sortTable('hora')">Hora <span class="sort-icon">↕</span></th>
    <th onclick="sortTable('irradiancia')">Irradiancia (W/m²) <span class="sort-icon">↕</span></th>
    <th>Calidad</th>`;
}

function dataColumnCount() {
  return anaKind === 'davis' ? 10 : 5;
}

function numberOrDash(value, decimals) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return num.toFixed(decimals);
}

function filterTable(q) {
  q = q.toLowerCase();
  tableFiltered = tableData.filter(r =>
    Object.values(r).some(value => String(value ?? '').toLowerCase().includes(q))
  );
  anaPage = 0;
  renderTablePage();
}

function sortTable(key) {
  if (anaSortKey === key) anaSortAsc = !anaSortAsc;
  else { anaSortKey = key; anaSortAsc = true; }
  renderTable();
}

function prevPage() {
  if (anaPage > 0) { anaPage--; renderTablePage(); }
}
function nextPage() {
  const pages = Math.ceil(tableFiltered.length / ANA_PAGE_SIZE);
  if (anaPage < pages - 1) { anaPage++; renderTablePage(); }
}

/* ----- Export CSV ----- */
function exportCSV() {
  if (!anaFiltered.length) { showToast('Carga datos primero', 'error'); return; }
  const columns = anaKind === 'davis'
    ? ['id','fecha','hora','solar_radiation_wm2','uv_index','temp_out_c','humidity_out','pressure_hpa','wind_speed_ms','quality','source']
    : ['id','fecha','hora','irradiancia'];
  const header = columns.join(',') + '\n';
  const rows = anaFiltered.map(r => columns.map(c => r[c] ?? '').join(',')).join('\n');
  const blob = new Blob([header + rows], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'irradiancia_export.csv'; a.click();
  URL.revokeObjectURL(url);
  showToast(`CSV exportado (${anaFiltered.length.toLocaleString()} filas)`);
}

/* Redraw analysis charts on resize */
window.addEventListener('resize', () => {
  if (document.getElementById('tab-datos').classList.contains('active') && anaFiltered.length) {
    drawHistChart();
    drawDistChart();
    drawHeatmap();
    drawHourlyChart();
  }
});
