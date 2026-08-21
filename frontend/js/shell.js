function getNavItems(role) {
  const items = [
    { key: 'status', label: '실시간 공정 상태 현황', icon: 'icon-clock.png', href: 'dashboard-status.html' },
    { key: 'detail', label: '공정 이상 상세', icon: 'icon-bell.png', href: '#' },
  ];

  if (role === 'manager') {
    items.push({ key: 'admin', label: '관리자 현황 확인', icon: 'icon-settings.png', href: 'admin-dashboard.html' });
  }

  return items;
}

const ROLE_LABEL = {
  worker: 'Worker Page',
  manager: 'Manager Page',
};

function formatScenarioClock(isoString) {
  if (!isoString) return '--:--:--';
  const d = new Date(isoString);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

let scenarioPollTimer = null;

function renderScenarioControl(status) {
  const el = document.getElementById('scenarioControl');
  if (!el) return;

  const statusText = !status.started
    ? '시작 전'
    : status.finished
      ? '재생 완료'
      : status.running
        ? '재생 중'
        : '일시정지됨';
  const hidePlayback = !status.started || status.finished;

  el.innerHTML = `
    <span class="scenario-status">${statusText}</span>
    <button type="button" id="scenarioStartBtn" ${status.started ? 'style="display:none"' : ''}>시작</button>
    <span class="scenario-clock">${formatScenarioClock(status.current_time)}</span>
    <button type="button" id="scenarioPauseBtn" ${hidePlayback || !status.running ? 'style="display:none"' : ''}>일시정지</button>
    <button type="button" id="scenarioResumeBtn" ${hidePlayback || status.running ? 'style="display:none"' : ''}>재생</button>
    <button type="button" id="scenarioRestartBtn" ${!status.started ? 'style="display:none"' : ''}>재시작</button>
  `;

  document.getElementById('scenarioStartBtn').addEventListener('click', async () => {
    renderScenarioControl(await startScenario());
  });
  document.getElementById('scenarioPauseBtn').addEventListener('click', async () => {
    renderScenarioControl(await pauseScenario());
  });
  document.getElementById('scenarioResumeBtn').addEventListener('click', async () => {
    renderScenarioControl(await resumeScenario());
  });
  document.getElementById('scenarioRestartBtn').addEventListener('click', async () => {
    localStorage.removeItem('maitech_variable_items');
    renderScenarioControl(await restartScenario());
  });

  if (scenarioPollTimer === null) {
    scenarioPollTimer = setInterval(() => {
      getScenarioStatus().then(renderScenarioControl);
    }, 1000);
  }
}

function renderAppShell({ active, role, mainHtml }) {
  const navHtml = getNavItems(role).map((item) => `
    <a class="nav-item${item.key === active ? ' active' : ''}" href="${item.href}">
      <img src="../images/${item.icon}" alt="">
      ${item.label}
    </a>
  `).join('');

  document.body.innerHTML = `
    <div class="app-shell">
      <header class="app-header">
        <a class="brand" href="dashboard-status.html">
          <img src="../images/logo.png" alt="MAITECH 로고">
          <span>MAITECH</span>
        </a>
        <div class="page-title">${ROLE_LABEL[role] || ''}</div>
        <div class="header-actions">
          <div class="search-box">
            <img src="../images/icon-search.png" alt="">
            <input type="text" placeholder="검색">
          </div>
          <div class="scenario-control" id="scenarioControl"></div>
          <div class="profile-menu">
            <button type="button" class="profile-icon" id="profileMenuBtn"><img src="../images/icon-profile.png" alt="프로필"></button>
            <div class="profile-dropdown" id="profileDropdown">
              <button type="button" id="logoutBtn">로그아웃</button>
            </div>
          </div>
        </div>
      </header>
      <div class="app-body">
        <nav class="sidebar">${navHtml}</nav>
        <main class="main-content" id="mainContent">${mainHtml || ''}</main>
      </div>
    </div>
  `;

  getScenarioStatus().then(renderScenarioControl);
  setupProfileMenu();
}

function setupProfileMenu() {
  const btn = document.getElementById('profileMenuBtn');
  const dropdown = document.getElementById('profileDropdown');

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('open');
  });

  document.addEventListener('click', () => {
    dropdown.classList.remove('open');
  });

  document.getElementById('logoutBtn').addEventListener('click', () => {
    sessionStorage.removeItem('maitech_user');
    window.location.href = '../index.html';
  });
}
