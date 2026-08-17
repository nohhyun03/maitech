const anomalyId = new URLSearchParams(window.location.search).get('id');

function renderSummary(event) {
  document.getElementById('summarySeverity').textContent = event.severity_grade;
  document.getElementById('summaryProcess').textContent = event.process_name;
  document.getElementById('summaryDetectedAt').textContent = formatDateTime(event.detected_at);
  document.getElementById('summaryDuration').textContent = formatDuration(event.duration_minutes);
  document.getElementById('summaryStatus').textContent = event.status;
}

function renderMetrics(event, prediction) {
  const topVariables = [...event.variables].sort((a, b) => b.score - a.score).slice(0, 3);
  const variableCards = topVariables.map((v) => `
    <div class="stat-card">
      <span class="badge">${v.variable_name}</span>
      <div class="value">${v.value}${v.unit ?? ''}</div>
      <div class="caption">${v.grade} · 기준 ${v.direction ?? ''}</div>
    </div>
  `).join('');

  const predictionCard = prediction ? `
    <div class="stat-card">
      <span class="badge">위험 예측</span>
      <div class="value">${prediction.impact_label}</div>
      <div class="caption">불량 가능성 ${prediction.confidence_pct.toFixed(1)}%</div>
    </div>
  ` : '';

  document.getElementById('metricGrid').innerHTML = variableCards + predictionCard;
}

function renderCauseTable(causes) {
  document.getElementById('causeTableBody').innerHTML = causes.map((c) => `
    <tr>
      <td>${c.variable_name}${c.unit ? ` (${c.unit})` : ''}</td>
      <td>${c.contribution_pct === 0 ? '0' : c.contribution_pct.toFixed(1)}%</td>
      <td>${c.current_value ?? '-'}</td>
      <td>${c.golden_value ?? '-'}</td>
      <td>${c.lower_bound ?? '-'}~${c.upper_bound ?? '-'}</td>
    </tr>
  `).join('');
}

function renderCauseList(causes) {
  document.getElementById('causeList').innerHTML = causes.map((c) => `
    <div class="cause-item">
      <div class="cause-rank"><span>${c.rank}순위</span><span>가능성 ${c.likelihood_pct.toFixed(1)}%</span></div>
      <div class="cause-name">${c.cause_name}</div>
      <div class="cause-desc">${c.description}</div>
    </div>
  `).join('');
}

let causesLoadingTimer = null;

function showCausesLoading() {
  causesLoadingTimer = setTimeout(() => {
    document.getElementById('causesStatus').textContent = 'AI 분석 중...';
  }, 400);
}

function hideCausesLoading() {
  clearTimeout(causesLoadingTimer);
  document.getElementById('causesStatus').textContent = '';
}

async function load() {
  document.getElementById('simulationLink').href = `dashboard-simulation?id=${anomalyId}`;

  const [event, prediction] = await Promise.all([
    getAnomaly(anomalyId),
    getQualityPrediction(anomalyId),
  ]);
  renderSummary(event);
  renderMetrics(event, prediction);

  showCausesLoading();
  const causeData = await getCauses(anomalyId);
  hideCausesLoading();
  renderCauseTable(causeData.variables);
  renderCauseList(causeData.causes);
}

load();
setInterval(load, 3000);
