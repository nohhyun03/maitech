const searchParams = new URLSearchParams(window.location.search);
const anomalyId = searchParams.get('id');
const selectedUpTo = Number(searchParams.get('upto')) || 0;

function buildActionContent(actions) {
  const sorted = [...actions].sort((a, b) => a.rank - b.rank);
  const taken = selectedUpTo > 0 ? sorted.filter((a) => a.rank <= selectedUpTo) : sorted;

  if (taken.length === 1) {
    return `${taken[0].action_name} 시행하여 정상화 확인됨.`;
  }

  const parts = taken.slice(0, -1).map((a, i) => {
    const lead = i === 0 ? '먼저' : '이어서';
    const outcome = i === 0 ? '해결되지 않아' : '역시 해결되지 않아';
    return `${lead} ${a.action_name} 시행하였으나 ${outcome}`;
  });
  const last = taken[taken.length - 1];
  const closing = taken.length > 2 ? '최종적으로' : '';
  parts.push(`${closing} ${last.action_name} 시행하여 해결함`.trim());

  return `${parts.join(' ')}.`;
}
const consentCheckbox = document.getElementById('consentCheckbox');
const submitBtn = document.getElementById('submitBtn');
const actionContent = document.getElementById('actionContent');

consentCheckbox.addEventListener('change', () => {
  submitBtn.disabled = !consentCheckbox.checked;
});

submitBtn.addEventListener('click', async () => {
  if (submitBtn.disabled) return;

  const currentUser = getCurrentUser();
  submitBtn.disabled = true;

  try {
    await submitActionRecord(anomalyId, {
      worker_id: currentUser.id,
      action_content: actionContent.value,
      extra_notes: document.getElementById('extraNotes').value,
    });
    alert('조치 기록이 저장되고 관리자에게 알림이 전송되었습니다.');
    window.location.href = 'dashboard-status.html';
  } catch (err) {
    alert('저장에 실패했습니다. 잠시 후 다시 시도해주세요.');
    submitBtn.disabled = false;
  }
});

async function load() {
  const currentUser = getCurrentUser();
  const [event, actions, scenario] = await Promise.all([
    getAnomaly(anomalyId),
    getRecommendedActions(anomalyId),
    getScenarioStatus(),
  ]);

  document.getElementById('infoProcess').textContent = event.process_name;
  document.getElementById('infoDetectedAt').textContent = formatDateTime(event.detected_at);
  document.getElementById('infoSeverity').textContent = event.severity_grade;
  document.getElementById('infoVariables').textContent = `${event.variables.map((v) => v.variable_name).join(', ')} 이상`;
  document.getElementById('infoId').textContent = event.id;
  document.getElementById('infoActionAt').textContent = scenario.current_time
    ? formatDateTime(scenario.current_time)
    : '-';
  document.getElementById('infoStatus').textContent = event.status;

  const senderLabel = currentUser.role === 'manager' ? '생산 관리자' : '현장 작업자';

  document.getElementById('senderOption').textContent = `${senderLabel} ${currentUser.name}`;
  document.getElementById('receiverOption').textContent = '생산 관리자 강성윤';

  document.getElementById('previewText').textContent =
    `[${event.id}] ${event.process_name} 이상 대응 조치 기록이 등록되었습니다. 조치 내용과 결과가 포함되며, 관리자는 이상 상세 화면에서 전체 기록을 확인할 수 있습니다.`;

  actionContent.value = buildActionContent(actions);
}

load();
