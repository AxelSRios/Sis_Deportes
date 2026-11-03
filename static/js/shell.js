/* ============================================================
   Sistema de Gestión Deportiva AFO · Oruro
   shell.js — shell compartido (sidebar + topbar) de navegación.
   Se activa solo en pantallas con data-shell="true".

   Adaptado a Django: las rutas de navegación y los datos del
   usuario se inyectan desde el servidor mediante window.AFO_URLS
   (ver templates), con fallback para despliegue en raíz.
   ============================================================ */
(function () {
  'use strict';

  var AFO = window.AFO_URLS || {};

  function createShell() {
    var body = document.body;
    if (body.getAttribute('data-shell') !== 'true') return;
    var page = body.getAttribute('data-page') || '';

    var CREST = 'https://lh3.googleusercontent.com/aida-public/AB6AXuB8YCfWLpvbLOv5_0kkRDxuET03XZgaxwHY7DpInL_KLkLauTEhyu_poqLxGl1TRKfCO8hneb04sIPI8oAXYAnkgvm1hsj3QKxCQd1_T90EXf3DbxCBnU_X77WTaS0WszWCfSzj2FPe_wsG-MOomlXWUweMSiXDwR57eVdTG0PhO1X-U_XQ--A7sExs2gDyH-NngieG32m8lbZvCKi55HzkXtw4hT5QPq8o1yW3v25ChD-9l2gza3VDYLN3Ady9Cx8biDo';

    var NAV = [
      { id: 'panel',       href: AFO.panel || '/panel-general/',            icon: 'dashboard',       label: 'Panel General' },
      { id: 'clubes',      href: AFO.clubes || '/clubes-equipos/',          icon: 'shield',          label: 'Clubes y Equipos' },
      { id: 'campeonatos', href: AFO.campeonatos || '/campeonatos-fixture/', icon: 'emoji_events',   label: 'Campeonatos y Fixture' },
      { id: 'arbitraje',   href: AFO.arbitraje || '/arbitraje-designaciones/', icon: 'sports',       label: 'Arbitraje y Designaciones' },
      { id: 'deportistas', href: AFO.deportistas || '/deportistas-fichajes/', icon: 'person_search', label: 'Deportistas y Fichajes' },
      { id: 'tesoreria',   href: AFO.tesoreria || '/tesoreria-pagos/',      icon: 'payments',        label: 'Tesorería y Pagos' },
      { id: 'auditoria',   href: AFO.auditoria || '/auditoria-usuarios/',   icon: 'manage_accounts', label: 'Auditoría y Usuarios' }
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

    var userDisplay = AFO.username || 'Administración';
    var userRole = AFO.role || 'Cómputo AFO';
    var initials = userDisplay
      .trim()
      .split(/\s+/)
      .map(function (w) { return w.charAt(0); })
      .join('')
      .substring(0, 2)
      .toUpperCase();

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
  '<a class="app-nav-item" href="' + (AFO.logout || '/logout/') + '">' +
    '<span class="material-symbols-outlined app-nav-icon">logout</span>' +
    '<span>Cerrar sesión</span>' +
  '</a>' +
'</div>' +
'</aside>' +
'<button class="app-sidebar-backdrop" id="app-backdrop" aria-label="Cerrar menú"></button>' +
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
            '<div class="app-avatar" title="' + userDisplay + '">' + initials + '</div>' +
            '<div class="app-user-meta"><strong>' + userDisplay + '</strong><span>' + userRole + '</span></div>' +
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