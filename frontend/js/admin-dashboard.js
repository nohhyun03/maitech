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

function renderStats(events, scenarioNow) {
  document.getElementById('statTotal').textContent = events.length;
  document.getElementById('statUnchecked').textContent = events.filter((e) => e.status === '미확인').length;
  document.getElementById('statCompleted').textContent = events.filter((e) => e.status === '조치완료' && !e.manager_confirmed).length;

  const dayAgo = new Date(scenarioNow).getTime() - 24 * 60 * 60 * 1000;
  document.getElementById('stat24h').textContent = events.filter((e) => new Date(e.detected_at).getTime() >= dayAgo).length;
}

let selectedAnomalyId = null;

function renderAlerts(events) {
  const list = document.getElementById('alertList');
  const sorted = [...events.filter((e) => !e.manager_confirmed), ...events.filter((e) => e.manager_confirmed)];

  list.innerHTML = sorted.map((e) => `
    <div class="alert-card ${e.id === selectedAnomalyId ? 'selected' : ''} ${e.manager_confirmed ? 'resolved' : ''}" data-id="${e.id}">
      <div>
        <div class="alert-title">
          <span class="severity-badge ${e.severity_grade === '긴급' ? 'urgent' : 'warning'}">${e.severity_grade}</span>
          ${e.process_name}
        </div>
        <div class="alert-meta">${e.variables.map((v) => v.variable_name).join(', ')} 이상 감지: ${formatDateTime(e.detected_at)}</div>
      </div>
      <div class="status-text ${statusClass(e.status)}">${e.manager_confirmed ? '관리자 확인 완료' : e.status}</div>
    </div>
  `).join('') || '<p style="color:#999; text-align:center;">알림이 없습니다.</p>';

  list.querySelectorAll('.alert-card').forEach((card) => {
    card.addEventListener('click', () => {
      selectedAnomalyId = selectedAnomalyId === card.dataset.id ? null : card.dataset.id;
      load();
    });
  });
}

function renderRecordDetailPlaceholder() {
  document.getElementById('recordDetail').innerHTML = '<p class="detail-placeholder">알림을 선택하세요.</p>';
}

function renderRecordDetail(event, record) {
  const varRows = event.variables.map((v) => `
    <div class="detail-variable-row">
      <span class="badge">${v.variable_name}</span>
      <span>${v.value}${v.unit ?? ''}</span>
      <span class="status-text ${statusClass(v.grade === '긴급' ? '미확인' : v.grade === '경고' ? '조치중' : '조치완료')}">${v.grade}</span>
    </div>
  `).join('');

  const actionSection = record
    ? `
      <div class="detail-action-content">
        <strong>수행 조치</strong> ${record.action_content}
        ${record.extra_notes ? `<div class="extra-notes"><strong>특이사항</strong> ${record.extra_notes}</div>` : ''}
      </div>
      <button type="button" class="detail-confirm-btn" id="detailConfirmBtn" ${record.manager_confirmed ? 'disabled' : ''}>
        ${record.manager_confirmed ? '관리자 확인 완료' : '관리자 확인'}
      </button>
    `
    : '<p class="detail-no-record">아직 조치 기록이 제출되지 않았습니다.</p>';

  document.getElementById('recordDetail').innerHTML = `
    <div class="detail-summary">
      <div class="detail-summary-row"><span class="detail-label">심각도</span><span>${event.severity_grade}</span></div>
      <div class="detail-summary-row"><span class="detail-label">공정명</span><span>${event.process_name}</span></div>
      <div class="detail-summary-row"><span class="detail-label">감지 시각</span><span>${formatDateTime(event.detected_at)}</span></div>
      <div class="detail-summary-row"><span class="detail-label">지속 시간</span><span>${formatDuration(event.duration_minutes)}</span></div>
      <div class="detail-summary-row"><span class="detail-label">상태</span><span>${event.status}</span></div>
    </div>
    <div class="detail-variables">${varRows}</div>
    <div class="detail-action-section">
      <span class="panel-label">조치 기록</span>
      ${actionSection}
    </div>
  `;

  const confirmBtn = document.getElementById('detailConfirmBtn');
  if (confirmBtn && !record.manager_confirmed) {
    confirmBtn.addEventListener('click', async () => {
      confirmBtn.disabled = true;
      confirmBtn.textContent = '관리자 확인 완료';
      await confirmActionRecord(record.id);
      await load();
    });
  }
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
  const [events, scenarioStatus] = await Promise.all([getAnomalies(), getScenarioStatus()]);
  document.getElementById('updatedAt').textContent = '마지막 업데이트: 방금 전';
  renderStats(events, scenarioStatus.current_time);
  renderAlerts(events);
  renderVariableList();

  if (!selectedAnomalyId) {
    renderRecordDetailPlaceholder();
    return;
  }

  const event = events.find((e) => e.id === selectedAnomalyId);
  if (!event) {
    selectedAnomalyId = null;
    renderRecordDetailPlaceholder();
    return;
  }

  const record = await getActionRecordFor(selectedAnomalyId);
  renderRecordDetail(event, record);
}

load();
setInterval(load, 3000);
