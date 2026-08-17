const API_BASE = 'http://localhost:8000';

function getCurrentUser() {
  const raw = sessionStorage.getItem('maitech_user');
  return raw ? JSON.parse(raw) : null;
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

function getAnomalies() {
  return apiGet('/api/anomalies');
}

function getAnomaly(id) {
  return getAnomalies().then((events) => events.find((e) => e.id === id));
}

function getVariables(id) {
  return apiGet(`/api/anomalies/${id}/variables`);
}

function getCauses(id) {
  return apiGet(`/api/anomalies/${id}/causes`);
}

function getQualityImpact(id) {
  return apiGet(`/api/anomalies/${id}/quality-impact`);
}

function getQualityPrediction(id) {
  return apiGet(`/api/anomalies/${id}/quality-prediction`);
}

function getRecommendedActions(id) {
  return apiGet(`/api/anomalies/${id}/recommended-actions`);
}

function startAction(id) {
  return apiPost(`/api/anomalies/${id}/start-action`);
}

function submitActionRecord(id, payload) {
  return apiPost(`/api/anomalies/${id}/action-records`, payload);
}

function getActionRecords() {
  return apiGet('/api/action-records');
}

function confirmActionRecord(id) {
  return apiPost(`/api/action-records/${id}/confirm`);
}

function getScenarioStatus() {
  return apiGet('/api/scenario/status');
}

function startScenario() {
  return apiPost('/api/scenario/start');
}

function restartScenario() {
  return apiPost('/api/scenario/restart');
}

function pauseScenario() {
  return apiPost('/api/scenario/pause');
}

function resumeScenario() {
  return apiPost('/api/scenario/resume');
}

function formatDateTime(isoString) {
  const d = new Date(isoString);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatDuration(totalMinutes) {
  const minutes = Math.floor(totalMinutes);
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return hours > 0 ? `${hours}시간 ${remainMinutes}분` : `${remainMinutes}분`;
}
