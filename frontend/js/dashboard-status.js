let ALERTS = [];
let currentFilter = 'all';

function severityOf(event) {
  return event.status === '조치완료' ? '해결' : event.severity_grade;
}

function renderAlerts() {
  const list = document.getElementById('alertList');
  const filtered = ALERTS.filter((e) => {
    if (currentFilter === 'all') return true;
    return severityOf(e) === currentFilter;
  });

  list.innerHTML = filtered.map((e) => `
    <div class="alert-card${e.status === '조치완료' ? ' resolved' : ''}">
      <div>
        <div class="alert-title">
          <span class="severity-badge ${e.severity_grade === '긴급' ? 'urgent' : 'warning'}">${e.severity_grade}</span>
          <a href="dashboard-detail?id=${e.id}">${e.process_name}</a>
        </div>
        <div class="alert-meta">감지 시점: ${formatDateTime(e.detected_at)}<br>${e.variables.map((v) => v.variable_name).join(', ')} 이상 - 상태: ${e.status}</div>
      </div>
      ${e.status === '조치완료' ? '<span class="resolve-btn" disabled>해결됨</span>' : ''}
    </div>
  `).join('') || '<p style="color:#999;">해당 조건의 알림이 없습니다.</p>';
}

function renderStats() {
  document.getElementById('statTotal').textContent = ALERTS.length;
  document.getElementById('statUrgent').textContent = ALERTS.filter((e) => e.status !== '조치완료' && e.severity_grade === '긴급').length;
  document.getElementById('statWarning').textContent = ALERTS.filter((e) => e.status !== '조치완료' && e.severity_grade === '경고').length;
  document.getElementById('statResolved').textContent = ALERTS.filter((e) => e.status === '조치완료').length;
}

document.getElementById('tabRow').addEventListener('click', (e) => {
  const btn = e.target.closest('.tab-button');
  if (!btn) return;
  document.querySelectorAll('.tab-button').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = btn.dataset.filter === '해결' ? '해결' : btn.dataset.filter;
  renderAlerts();
});

async function load() {
  ALERTS = await getAnomalies();
  document.getElementById('updatedAt').textContent = '마지막 업데이트: 방금 전';
  renderStats();
  renderAlerts();
}

load();
