const CLOCK_ICON_SVG = `
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/>
    <path d="M12 7v5l3.5 3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
`;

const BELL_ICON_SVG = `
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6 10a6 6 0 1 1 12 0c0 3.2 1 4.8 2 6H4c1-1.2 2-2.8 2-6Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>
`;

const GEAR_ICON_SVG = `
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/>
    <path d="M12 3v2.5M12 18.5V21M21 12h-2.5M5.5 12H3M18.5 5.5l-1.8 1.8M7.3 16.7l-1.8 1.8M18.5 18.5l-1.8-1.8M7.3 7.3 5.5 5.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>
`;

const SIMULATION_ICON_SVG = `
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2L4 5V11C4 16.55 7.84 21.74 12 23C16.16 21.74 20 16.55 20 11V5L12 2Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M8.5 12.2L11 14.7L15.8 9.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
`;

const ACTION_RECORD_ICON_SVG = `
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M14 3v5h5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M9 14h6M9 17h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
`;

const DRILLDOWN_CHAIN = [
  { key: 'detail', label: '공정 이상 상세', iconSvg: BELL_ICON_SVG, page: 'dashboard-detail' },
  { key: 'simulation', label: '시뮬레이션 진행', iconSvg: SIMULATION_ICON_SVG, page: 'dashboard-simulation' },
  { key: 'action-record', label: '조치 기록 작성', iconSvg: ACTION_RECORD_ICON_SVG, page: 'action-record' },
];

function getNavItems(role, active) {
  const items = [
    { key: 'status', label: '실시간 공정 상태 현황', iconSvg: CLOCK_ICON_SVG, href: 'dashboard-status.html' },
  ];

  const activeIndex = DRILLDOWN_CHAIN.findIndex((item) => item.key === active);
  if (activeIndex !== -1) {
    DRILLDOWN_CHAIN.slice(0, activeIndex + 1).forEach((item, i) => {
      const isCurrent = i === activeIndex;
      items.push({
        key: item.key,
        label: item.label,
        iconSvg: item.iconSvg,
        subLevel: true,
        nonNavigable: isCurrent,
        href: isCurrent ? undefined : `${item.page}${window.location.search}`,
      });
    });
  }

  if (role === 'manager') {
    items.push({ key: 'admin', label: '관리자 현황 확인', iconSvg: GEAR_ICON_SVG, href: 'admin-dashboard.html' });
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
    await restartScenario();
    window.location.href = 'dashboard-status.html';
  });

  if (scenarioPollTimer === null) {
    scenarioPollTimer = setInterval(() => {
      getScenarioStatus().then(renderScenarioControl);
    }, 1000);
  }
}

function renderAppShell({ active, role, mainHtml }) {
  const navHtml = getNavItems(role, active).map((item) => {
    const classes = `nav-item${item.key === active ? ' active' : ''}${item.subLevel ? ' nav-sub' : ''}`;
    const inner = `
      ${item.iconSvg}
      ${item.label}
    `;
    return item.nonNavigable
      ? `<span class="${classes}">${inner}</span>`
      : `<a class="${classes}" href="${item.href}">${inner}</a>`;
  }).join('');

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
