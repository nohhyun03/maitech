const ALERTS = [
  { id: 'a3', severity: '긴급', title: '긴급 압출 공정 A-3', time: '2026.08.15 00:46', desc: '용융 온도 이상 - 기준 패턴 대비 편차 18%', resolved: false },
  { id: 'b8', severity: '긴급', title: '긴급 냉각 공정 B-8', time: '2026.08.14 23:52', desc: '냉각수 유량 저하 - 기준 패턴 대비 편차 22%', resolved: false },
  { id: 'c3', severity: '긴급', title: '긴급 혼합 공정 C-3', time: '2026.08.14 18:23', desc: '교반 속도 불안정 - 패턴 이탈 지속 7분', resolved: false },
  { id: 'a1', severity: '경고', title: '경고 압출 공정 A-1', time: '2026.08.14 09:07', desc: '압력 변동 반복 - 3회 연속 경계값 초과', resolved: false },
];

let currentFilter = 'all';

function renderAlerts() {
  const list = document.getElementById('alertList');
  const filtered = ALERTS.filter((a) => {
    if (currentFilter === 'all') return true;
    if (currentFilter === '해결') return a.resolved;
    return a.severity === currentFilter && !a.resolved;
  });

  list.innerHTML = filtered.map((a) => `
    <div class="alert-card${a.resolved ? ' resolved' : ''}">
      <div>
        <div class="alert-title"><a href="dashboard-detail.html?id=${a.id}">${a.title}</a></div>
        <div class="alert-meta">감지 시점: ${a.time}<br>${a.desc}</div>
      </div>
      <button class="resolve-btn" data-id="${a.id}" ${a.resolved ? 'disabled' : ''}>${a.resolved ? '해결됨' : '해결'}</button>
    </div>
  `).join('') || '<p style="color:#999;">해당 조건의 알림이 없습니다.</p>';

  list.querySelectorAll('.resolve-btn:not([disabled])').forEach((btn) => {
    btn.addEventListener('click', () => {
      const alert = ALERTS.find((a) => a.id === btn.dataset.id);
      alert.resolved = true;
      applyStatDelta(alert.severity);
      renderAlerts();
    });
  });
}

function applyStatDelta(severity) {
  const el = severity === '긴급' ? document.getElementById('statUrgent') : document.getElementById('statWarning');
  const resolvedEl = document.getElementById('statResolved');
  el.textContent = Math.max(0, Number(el.textContent) - 1);
  resolvedEl.textContent = Number(resolvedEl.textContent) + 1;
}

document.getElementById('tabRow').addEventListener('click', (e) => {
  const btn = e.target.closest('.tab-button');
  if (!btn) return;
  document.querySelectorAll('.tab-button').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = btn.dataset.filter;
  renderAlerts();
});

renderAlerts();
