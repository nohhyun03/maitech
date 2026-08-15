const METRICS = [
  { badge: '압출 온도 편차', value: '+18.4℃', caption: '기준 대비 초과' },
  { badge: '압력 변동 폭', value: '3.8 Mpa', caption: '정상 범위 초과' },
  { badge: '라인 속도 이탈', value: '-11.7%', caption: '정상 범위 초과' },
  { badge: '불량 예측 위험', value: '높음', caption: '정상 범위 초과' },
];

const CAUSES = [
  { rank: '1순위', contribution: '기여도 71%', name: '가열 히터 응답 지연', desc: '히터 PID 제어 응답이 지연되며 온도 편차가 누적된 패턴과 일치합니다.' },
  { rank: '2순위', contribution: '기여도 28%', name: '원료 점도 변화', desc: '원료 배치 교체 이후 점도 상승이 감지되어 압력 변동에 영향을 주고 있습니다.' },
  { rank: '3순위', contribution: '기여도 5%', name: '냉각 구간 이상', desc: '냉각 수온 편차가 라인 속도 이탈과 복합적으로 작용하고 있습니다.' },
];

const CAUSE_TABLE_ROW_COUNT = 5;

function renderMetrics() {
  document.getElementById('metricGrid').innerHTML = METRICS.map((m) => `
    <div class="stat-card">
      <span class="badge">${m.badge}</span>
      <div class="value">${m.value}</div>
      <div class="caption">${m.caption}</div>
    </div>
  `).join('');
}

function renderCauseTable() {
  const row = `<tr>${'<td><span class="skeleton"></span></td>'.repeat(4)}</tr>`;
  document.getElementById('causeTableBody').innerHTML = row.repeat(CAUSE_TABLE_ROW_COUNT);
}

function renderCauseList() {
  document.getElementById('causeList').innerHTML = CAUSES.map((c) => `
    <div class="cause-item">
      <div class="cause-rank"><span>${c.rank}</span><span>${c.contribution}</span></div>
      <div class="cause-name">${c.name}</div>
      <div class="cause-desc">${c.desc}</div>
    </div>
  `).join('');
}

renderMetrics();
renderCauseTable();
renderCauseList();
