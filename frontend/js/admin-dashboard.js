const VARIABLE_ITEMS = [
  {
    process: '패키징 공정',
    variables: ['금형 온도', '사출 압력', '수지 양', '수지 점도 (모터 부하)', '유량 (RAM 속도)', '몰딩 시간', '냉각 속도', '작업장 습도', '진공 시간'],
  },
  {
    process: '다이 본딩 공정',
    variables: ['본딩 온도', '가압력', '다이 위치 정밀도', '본딩 시간', '접착제 도포량'],
  },
  {
    process: '와이어 본딩 공정',
    variables: ['와이어 장력', '초음파 출력', '루프 높이', '본딩 온도', '본딩 시간'],
  },
];

function statusClass(status) {
  if (status === '미확인') return 'status-unchecked';
  if (status === '조치중') return 'status-checking';
  return 'status-done';
}

function renderStats(events) {
  document.getElementById('statTotal').textContent = events.length;
  document.getElementById('statUnchecked').textContent = events.filter((e) => e.status === '미확인').length;
  document.getElementById('statInProgress').textContent = events.filter((e) => e.status === '조치중').length;

  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  document.getElementById('stat24h').textContent = events.filter((e) => new Date(e.detected_at).getTime() >= dayAgo).length;
}

function renderAlerts(events) {
  const list = document.getElementById('alertList');
  list.innerHTML = events.map((e) => `
    <div class="alert-card">
      <div>
        <div class="alert-title">${e.severity_grade} ${e.process_name}</div>
        <div class="alert-meta">${e.variables.map((v) => v.variable_name).join(', ')} 이상 감지: ${formatDateTime(e.detected_at)}</div>
      </div>
      <div class="status-text ${statusClass(e.status)}">${e.status}</div>
    </div>
  `).join('') || '<p style="color:#999;">알림이 없습니다.</p>';
}

const expandedRecordIds = new Set();

function renderRecordTable(records) {
  const body = document.getElementById('recordTableBody');
  body.innerHTML = records.map((r) => {
    const expanded = expandedRecordIds.has(String(r.id));
    return `
    <tr data-row-id="${r.id}">
      <td>${r.process_name}</td>
      <td>${r.issue_type}</td>
      <td>
        <div class="action-content-cell ${expanded ? 'expanded' : 'collapsed'}">
          <strong>수행 조치</strong> ${r.action_content}
          ${r.extra_notes ? `<div class="extra-notes"><strong>특이사항</strong> ${r.extra_notes}</div>` : ''}
        </div>
        <button type="button" class="expand-toggle" data-id="${r.id}">${expanded ? '접기' : '자세히 보기'}</button>
      </td>
      <td>
        <input type="checkbox" class="confirm-checkbox" data-id="${r.id}">
      </td>
    </tr>
  `;
  }).join('') || '<tr><td colspan="4" style="color:#999;">확인 대기 중인 조치 기록이 없습니다.</td></tr>';

  body.querySelectorAll('.expand-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cell = btn.previousElementSibling;
      const expanded = cell.classList.toggle('expanded');
      cell.classList.toggle('collapsed', !expanded);
      btn.textContent = expanded ? '접기' : '자세히 보기';
      if (expanded) {
        expandedRecordIds.add(btn.dataset.id);
      } else {
        expandedRecordIds.delete(btn.dataset.id);
      }
    });
  });

  body.querySelectorAll('.confirm-checkbox').forEach((box) => {
    box.addEventListener('change', async () => {
      box.disabled = true;
      await confirmActionRecord(box.dataset.id);
      body.querySelector(`tr[data-row-id="${box.dataset.id}"]`)?.remove();
      if (!body.querySelector('tr')) {
        body.innerHTML = '<tr><td colspan="4" style="color:#999;">확인 대기 중인 조치 기록이 없습니다.</td></tr>';
      }
    });
  });
}

function renderVariableList() {
  const list = document.getElementById('variableList');
  list.innerHTML = VARIABLE_ITEMS.map((v) => `
    <div class="variable-item">
      <div class="variable-title">분석 대상: ${v.process}</div>
      <div class="variable-sub">공정 변수</div>
      <div class="chip-row">${v.variables.map((name) => `<span class="chip">${name}</span>`).join('')}</div>
    </div>
  `).join('');
}

async function load() {
  const [events, records] = await Promise.all([getAnomalies(), getActionRecords()]);
  document.getElementById('updatedAt').textContent = '마지막 업데이트: 방금 전';
  renderStats(events);
  renderAlerts(events);
  renderRecordTable(records);
  renderVariableList();
}

load();
setInterval(load, 3000);
