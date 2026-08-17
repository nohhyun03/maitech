const anomalyId = new URLSearchParams(window.location.search).get('id');

function renderImpact(impacts) {
  document.getElementById('impactGrid').innerHTML = impacts.map((impact) => `
    <div class="stat-card impact-card">
      <span class="badge">${impact.label}</span>
      <div class="impact-desc">${impact.description}</div>
    </div>
  `).join('');
}

function renderSimTable(actions) {
  const seen = new Set();
  const rows = actions.filter((a) => {
    if (seen.has(a.variable_name)) return false;
    seen.add(a.variable_name);
    return true;
  });

  document.getElementById('simTableBody').innerHTML = rows.map((a) => `
    <tr>
      <td>${a.variable_name}</td>
      <td>${a.current_value}${a.unit}</td>
      <td>${a.target_value.toFixed(1)}${a.unit}</td>
      <td>${a.expected_effect}</td>
    </tr>
  `).join('');
}

function renderActions(actions) {
  const list = document.getElementById('actionList');
  list.innerHTML = actions.map((a) => `
    <div class="cause-item">
      <div class="cause-rank">
        <span>조치${a.rank}</span>
        <span>${a.priority}</span>
      </div>
      <div class="cause-name">${a.action_name}</div>
      <div class="cause-desc">${a.description}</div>
    </div>
  `).join('');
}

async function load() {
  await startAction(anomalyId);

  document.getElementById('actionRecordLink').href = `action-record?id=${anomalyId}`;

  const [prediction, impact, actions] = await Promise.all([
    getQualityPrediction(anomalyId),
    getQualityImpact(anomalyId),
    getRecommendedActions(anomalyId),
  ]);

  document.getElementById('confidenceLine').textContent = `예측 신뢰도: ${prediction.confidence_pct.toFixed(1)}%`;
  renderImpact(impact);
  renderSimTable(actions);
  renderActions(actions);
}

load();
setInterval(load, 3000);
