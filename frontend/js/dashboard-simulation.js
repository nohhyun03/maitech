const IMPACTS = [
  {
    label: '치수 불량 발생 가능성',
    desc: '현재 패턴이 15분 이상 지속될 경우 압출 단면 치수 편차 불량률이 약 8~14% 수준으로 상승할 것으로 추정됩니다.',
  },
  {
    label: '표면 결함 위험',
    desc: '온도 편차가 해소되지 않으면 완성품 표면에 줄기 형태의 결함이 발생할 수 있습니다.',
  },
  {
    label: '강도 저하 가능성',
    desc: '냉각 불균일에 의한 내부 응력 집중으로 인장 강도가 기준 대비 최대 6% 저하될 수 있습니다.',
  },
];

const ACTIONS = [
  {
    rank: '조치1',
    priority: '즉시',
    name: '히터 온도 설정값 재조정',
    desc: 'A-3 라인 히터 설정값을 215℃→210℃로 낮추고 PID 응답 시간을 5초로 단축하는 것을 검토하십시오.',
  },
  {
    rank: '조치2',
    priority: '30분 이내',
    name: '원료 배치 점도 재확인',
    desc: '현재 투입 중인 원료 배치의 점도 데이터를 확인하고 이전 배치와 비교하십시오.',
  },
  {
    rank: '조치3',
    priority: '순차 처리',
    name: '냉각 수온 점검',
    desc: '냉각 구간 수온이 설정 범위(18℃~22℃) 이내인지 현장에서 직접 확인하십시오.',
  },
];

function renderImpacts() {
  const grid = document.getElementById('impactGrid');
  grid.innerHTML = IMPACTS.map((item) => `
    <div class="stat-card impact-card">
      <span class="badge">${item.label}</span>
      <div class="impact-desc">${item.desc}</div>
    </div>
  `).join('');
}

function renderSimTable() {
  const tbody = document.getElementById('simTableBody');
  tbody.innerHTML = Array.from({ length: 5 }).map(() => `
    <tr>
      <td><span class="skeleton"></span></td>
      <td><span class="skeleton"></span></td>
      <td><span class="skeleton"></span></td>
      <td><span class="skeleton"></span></td>
    </tr>
  `).join('');
}

function renderActions() {
  const list = document.getElementById('actionList');
  list.innerHTML = ACTIONS.map((a) => `
    <div class="cause-item">
      <div class="cause-rank">
        <span>${a.rank}</span>
        <span>${a.priority}</span>
      </div>
      <div class="cause-name">${a.name}</div>
      <div class="cause-desc">${a.desc}</div>
    </div>
  `).join('');
}

renderImpacts();
renderSimTable();
renderActions();
