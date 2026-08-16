const ALERTS = [
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '미확인' },
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '조치중' },
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '조치중' },
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '조치 완료' },
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '조치중' },
  { title: '긴급 압출 공정 A-4', desc: '압력 저하 감지: 2026.08.16 09:12', status: '조치완료' },
];

const RECORD_ROW_COUNT = 5;
const TABLE_COLUMNS = 4;

const VARIABLE_ITEMS = [
  { target: '분석 대상: 압축 공정 A-4', sub: '주요 변수 요소', chipCount: 8 },
  { target: '분석 대상: 압축 공정 A-4', sub: '주요 변수 요소', chipCount: 8 },
  { target: '분석 대상: 압축 공정 A-4', sub: '주요 변수 요소', chipCount: 8 },
];

function statusClass(status) {
  if (status === '미확인') return 'status-unchecked';
  if (status === '조치중') return 'status-checking';
  return 'status-done';
}

function renderAlerts() {
  const list = document.getElementById('alertList');
  list.innerHTML = ALERTS.map((a) => `
    <div class="alert-card">
      <div>
        <div class="alert-title">${a.title}</div>
        <div class="alert-meta">${a.desc}</div>
      </div>
      <div class="status-text ${statusClass(a.status)}">${a.status}</div>
    </div>
  `).join('');
}

function renderRecordTable() {
  const body = document.getElementById('recordTableBody');
  const row = `<tr>${'<td><span class="skeleton"></span></td>'.repeat(TABLE_COLUMNS)}</tr>`;
  body.innerHTML = row.repeat(RECORD_ROW_COUNT);
}

function renderVariableList() {
  const list = document.getElementById('variableList');
  list.innerHTML = VARIABLE_ITEMS.map((v) => `
    <div class="variable-item">
      <div class="variable-title">${v.target}</div>
      <div class="variable-sub">${v.sub}</div>
      <div class="chip-row">${'<span class="chip-skeleton"></span>'.repeat(v.chipCount)}</div>
    </div>
  `).join('');
}

renderAlerts();
renderRecordTable();
renderVariableList();
