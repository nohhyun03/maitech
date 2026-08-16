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
        <div class="brand">
          <img src="../images/logo.png" alt="MAITECH 로고">
          <span>MAITECH</span>
        </div>
        <div class="page-title">${ROLE_LABEL[role] || ''}</div>
        <div class="header-actions">
          <div class="search-box">
            <img src="../images/icon-search.png" alt="">
            <input type="text" placeholder="검색">
          </div>
          <div class="profile-icon"><img src="../images/icon-profile.png" alt="프로필"></div>
        </div>
      </header>
      <div class="app-body">
        <nav class="sidebar">${navHtml}</nav>
        <main class="main-content" id="mainContent">${mainHtml || ''}</main>
      </div>
    </div>
  `;
}
