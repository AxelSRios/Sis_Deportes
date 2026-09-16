/* ============================================================
   Sistema de Gestión Deportiva AFO · Oruro
   shell.js — shell compartido (sidebar + topbar) de navegación.
   Se activa solo en pantallas con data-shell="true".
   ============================================================ */
(function () {
  'use strict';

  function createShell() {
    var body = document.body;
    if (body.getAttribute('data-shell') !== 'true') return;
    var page = body.getAttribute('data-page') || '';

    var CREST = 'https://lh3.googleusercontent.com/aida-public/AB6AXuB8YCfWLpvbLOv5_0kkRDxuET03XZgaxwHY7DpInL_KLkLauTEhyu_poqLxGl1TRKfCO8hneb04sIPI8oAXYAnkgvm1hsj3QKxCQd1_T90EXf3DbxCBnU_X77WTaS0WszWCfSzj2FPe_wsG-MOomlXWUweMSiXDwR57eVdTG0PhO1X-U_XQ--A7sExs2gDyH-NngieG32m8lbZvCKi55HzkXtw4hT5QPq8o1yW3v25ChD-9l2gza3VDYLN3Ady9Cx8biDo';

    var NAV = [
      { id: 'panel',       href: '02-panel-general.html',            icon: 'dashboard',      label: 'Panel General' },
      { id: 'clubes',      href: '03-clubes-y-equipos.html',         icon: 'shield',         label: 'Clubes y Equipos' },
      { id: 'campeonatos', href: '04-campeonatos-y-fixture.html',    icon: 'emoji_events',   label: 'Campeonatos y Fixture' },
      { id: 'arbitraje',   href: '05-arbitraje-y-designaciones.html', icon: 'sports',        label: 'Arbitraje y Designaciones' },
      { id: 'deportistas', href: '06-deportistas-y-fichajes.html',   icon: 'person_search',  label: 'Deportistas y Fichajes' },
      { id: 'tesoreria',   href: '07-tesoreria-y-pagos.html',        icon: 'payments',       label: 'Tesorería y Pagos' },
      { id: 'auditoria',   href: '08-auditoria-y-usuarios.html',     icon: 'manage_accounts', label: 'Auditoría y Usuarios' }
    ];

    var TITLES = {
      panel:       'Panel General',
      clubes:      'Clubes y Equipos',
      campeonatos: 'Campeonatos y Fixture',
      arbitraje:   'Arbitraje y Designaciones',
      deportistas: 'Deportistas y Fichajes',
      tesoreria:   'Tesorería y Pagos',
      auditoria:   'Auditoría y Usuarios'
    };

    var navHtml = '';
    for (var i = 0; i < NAV.length; i++) {
      var n = NAV[i];
      var cls = 'app-nav-item' + (n.id === page ? ' app-nav-item-active' : '');
      navHtml += '<a class="' + cls + '" href="' + n.href + '">' +
                 '<span class="material-symbols-outlined app-nav-icon">' + n.icon + '</span>' +
                 '<span>' + n.label + '</span></a>';
    }

    var shell = document.createElement('div');
    shell.className = 'app-shell';
    shell.innerHTML =
      '<aside class="app-shell-sidebar" id="app-sidebar">' +
        '<div class="app-sidebar-head">' +
          '<img class="app-sidebar-crest" src="' + CREST + '" alt="Escudo Asociación de Fútbol Oruro"/>' +
          '<div><strong>AFO · Oruro</strong><span>Asociación de Fútbol</span></div>' +
        '</div>' +
        '<nav class="app-sidebar-nav">' + navHtml + '</nav>' +
        '<div class="app-sidebar-foot">' +
          '<a class="app-nav-item" href="01-iniciar-sesion.html">' +
            '<span class="material-symbols-outlined app-nav-icon">logout</span>' +
            '<span>Cerrar sesión</span>' +
          '</a>' +
        '</div>' +
        '<button class="app-sidebar-backdrop" id="app-backdrop" aria-label="Cerrar menú"></button>' +
      '</aside>' +
      '<header class="app-shell-topbar">' +
        '<button class="app-topbar-burger" id="app-menu-toggle" aria-label="Abrir menú">' +
          '<span class="material-symbols-outlined">menu</span>' +
        '</button>' +
        '<div class="app-topbar-title">' +
          '<span>Consola Administrativa</span>' +
          '<strong>' + (TITLES[page] || 'Portal AFO') + '</strong>' +
        '</div>' +
        '<div class="app-topbar-actions">' +
          '<label class="app-search">' +
            '<span class="material-symbols-outlined">search</span>' +
            '<input type="search" placeholder="Buscar en el sistema…"/>' +
          '</label>' +
          '<button class="app-icon-btn" aria-label="Notificaciones">' +
            '<span class="material-symbols-outlined">notifications</span>' +
            '<span class="app-dot"></span>' +
          '</button>' +
          '<div class="app-user">' +
            '<div class="app-avatar">AD</div>' +
            '<div class="app-user-meta"><strong>Administración</strong><span>Cómputo AFO</span></div>' +
          '</div>' +
        '</div>' +
      '</header>';

    body.prepend(shell);

    var toggle = document.getElementById('app-menu-toggle');
    var backdrop = document.getElementById('app-backdrop');
    if (toggle) {
      toggle.addEventListener('click', function () {
        body.classList.toggle('app-shell-open');
      });
    }
    if (backdrop) {
      backdrop.addEventListener('click', function () {
        body.classList.remove('app-shell-open');
      });
    }
    document.addEventListener('keyup', function (e) {
      if (e.key === 'Escape') body.classList.remove('app-shell-open');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createShell);
  } else {
    createShell();
  }
})();