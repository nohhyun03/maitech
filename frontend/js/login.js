const ROLE_HOME = {
  worker: 'pages/dashboard-status.html',
  manager: 'pages/admin-dashboard.html',
};

const REMEMBERED_ID_KEY = 'maitech_remembered_id';

const rememberedId = localStorage.getItem(REMEMBERED_ID_KEY);
if (rememberedId) {
  document.getElementById('loginId').value = rememberedId;
  document.getElementById('rememberMe').checked = true;
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const errorEl = document.getElementById('loginError');
  errorEl.style.display = 'none';

  const username = document.getElementById('loginId').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (document.getElementById('rememberMe').checked) {
    localStorage.setItem(REMEMBERED_ID_KEY, username);
  } else {
    localStorage.removeItem(REMEMBERED_ID_KEY);
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      errorEl.textContent = body.detail || '로그인에 실패했습니다.';
      errorEl.style.display = 'block';
      return;
    }

    const user = await res.json();
    sessionStorage.setItem('maitech_user', JSON.stringify(user));
    window.location.href = ROLE_HOME[user.role] || ROLE_HOME.worker;
  } catch (err) {
    errorEl.textContent = '서버에 연결할 수 없습니다.';
    errorEl.style.display = 'block';
  }
});
