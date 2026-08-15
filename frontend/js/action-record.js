const consentCheckbox = document.getElementById('consentCheckbox');
const submitBtn = document.getElementById('submitBtn');

consentCheckbox.addEventListener('change', () => {
  submitBtn.disabled = !consentCheckbox.checked;
});

submitBtn.addEventListener('click', () => {
  if (submitBtn.disabled) return;
  alert('조치 기록이 저장되고 관리자에게 알림이 전송되었습니다.');
  window.location.href = 'dashboard-status.html';
});
