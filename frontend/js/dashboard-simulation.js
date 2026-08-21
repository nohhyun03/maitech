const anomalyId = new URLSearchParams(window.location.search).get('id');
let selectedUpTo = 0;

function renderImpact(impacts) {
  document.getElementById('impactGrid').innerHTML = impacts.map((impact) => `
    <div class="stat-card impact-card">
      <span class="badge">${impact.label}</span>
      <div class="impact-desc">${impact.description}</div>
    </div>
  `).join('');
}

function renderImpactLoading() {
  document.getElementById('impactGrid').innerHTML = `
    <div class="cause-item-loading impact-loading">AI가 예상 품질 영향을 분석하고 있습니다...</div>
  `;
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

function updateActionRecordLink() {
  const link = document.getElementById('actionRecordLink');
  link.href = selectedUpTo > 0
    ? `action-record?id=${anomalyId}&upto=${selectedUpTo}`
    : `action-record?id=${anomalyId}`;
}

function renderActions(actions) {
  const list = document.getElementById('actionList');
  list.innerHTML = actions.map((a) => `
    <div class="cause-item${a.rank <= selectedUpTo ? ' selected' : ''}" data-rank="${a.rank}">
      <div class="cause-rank">
        <span>조치${a.rank}</span>
        <span>${a.priority}</span>
      </div>
      <div class="cause-name">${a.action_name}</div>
      <div class="cause-desc">${a.description}</div>
    </div>
  `).join('');

  list.querySelectorAll('.cause-item').forEach((el) => {
    el.addEventListener('click', () => {
      const rank = Number(el.dataset.rank);
      selectedUpTo = selectedUpTo === rank ? 0 : rank;
      renderActions(actions);
      updateActionRecordLink();
    });
  });
}

function renderActionsLoading() {
  document.getElementById('actionList').innerHTML = `
    <div class="cause-item cause-item-loading">AI가 권장 조치를 정리하고 있습니다...</div>
  `;
}

async function load() {
  await startAction(anomalyId);

  document.getElementById('actionRecordLink').href = `action-record?id=${anomalyId}`;

  renderActionsLoading();
  renderImpactLoading();

  const actions = await getRecommendedActions(anomalyId);

  renderSimTable(actions);
  renderActions(actions);

  const impact = await getQualityImpact(anomalyId);
  renderImpact(impact);
}

load();
