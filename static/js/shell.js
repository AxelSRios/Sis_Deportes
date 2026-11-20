/* ============================================================
   Sistema de Gestión Deportiva AFO · Oruro
   shell.js — shell compartido (sidebar + topbar) de navegación.
   Se activa solo en pantallas con data-shell="true".

   Las rutas y los datos del usuario llegan desde el servidor en
   window.AFO_URLS. El módulo activo se deduce de la ruta actual,
   de modo que listas, fichas y formularios resaltan su sección.
   ============================================================ */
(function () {
  'use strict';

  var AFO = window.AFO_URLS || {};

  function createShell() {
    var body = document.body;
    if (body.getAttribute('data-shell') !== 'true') return;

    var CREST = 'https://lh3.googleusercontent.com/aida-public/AB6AXuB8YCfWLpvbLOv5_0kkRDxuET03XZgaxwHY7DpInL_KLkLauTEhyu_poqLxGl1TRKfCO8hneb04sIPI8oAXYAnkgvm1hsj3QKxCQd1_T90EXf3DbxCBnU_X77WTaS0WszWCfSzj2FPe_wsG-MOomlXWUweMSiXDwR57eVdTG0PhO1X-U_XQ--A7sExs2gDyH-NngieG32m8lbZvCKi55HzkXtw4hT5QPq8o1yW3v25ChD-9l2gza3VDYLN3Ady9Cx8biDo';

    var NAV = [
      { id: 'panel',        href: AFO.panel || '/panel-general/',          icon: 'dashboard',        label: 'Panel General',              group: 'Principal' },
      { id: 'clubes',       href: AFO.clubes || '/clubes/',                icon: 'shield',           label: 'Clubes',                     group: 'Gestión deportiva' },
      { id: 'equipos',      href: AFO.equipos || '/equipos/',              icon: 'groups',           label: 'Equipos',                    group: 'Gestión deportiva' },
      { id: 'deportistas',  href: AFO.deportistas || '/deportistas/',      icon: 'person_search',    label: 'Deportistas',                group: 'Gestión deportiva' },
      { id: 'categorias',   href: AFO.categorias || '/categorias/',        icon: 'category',         label: 'Categorías',                 group: 'Gestión deportiva' },
      { id: 'campeonatos',  href: AFO.campeonatos || '/campeonatos/',      icon: 'emoji_events',     label: 'Campeonatos',                group: 'Competencia' },
      { id: 'inscripciones',href: AFO.inscripciones || '/inscripciones/',  icon: 'fact_check',       label: 'Inscripciones',              group: 'Competencia' },
      { id: 'partidos',     href: AFO.partidos || '/partidos/',            icon: 'sports_soccer',    label: 'Partidos',                   group: 'Competencia' },
      { id: 'arbitros',     href: AFO.arbitros || '/arbitros/',            icon: 'sports',           label: 'Árbitros',                   group: 'Competencia' },
      { id: 'asignaciones', href: AFO.asignaciones || '/asignaciones/',    icon: 'assignment_ind',   label: 'Asignaciones arbitrales',    group: 'Competencia' },
      { id: 'sanciones',    href: AFO.sanciones || '/sanciones/',          icon: 'gavel',            label: 'Sanciones',                  group: 'Competencia' },
      { id: 'tesoreria',    href: AFO.tesoreria || '/tesoreria/',          icon: 'payments',         label: 'Tesorería y Pagos',          group: 'Administración' },
      { id: 'reportes',     href: AFO.reportes || '/reportes/',            icon: 'summarize',        label: 'Reportes',                   group: 'Administración' },
      { id: 'usuarios',     href: AFO.usuarios || '/usuarios/',            icon: 'manage_accounts',  label: 'Usuarios',                   group: 'Administración' },
      { id: 'auditoria',    href: AFO.auditoria || '/auditoria/',          icon: 'history',          label: 'Historial de operaciones',   group: 'Administración' },
      { id: 'perfil',       href: AFO.perfil || '/perfil/',                icon: 'account_circle',   label: 'Mi perfil',                  group: 'Cuenta' }
    ];

    // Accesos reservados por responsabilidad. El servidor vuelve a validar el
    // rol en cada vista (403); esto solo evita mostrar enlaces sin salida.
    var ADMIN_LABEL = 'Administrador General de la A.F.O.';
    var FINANZAS_LABEL = 'Tesorero / Finanzas Institucionales';
    var ACCESO_POR_ROL = {
      tesoreria: [ADMIN_LABEL, FINANZAS_LABEL],
      usuarios: [ADMIN_LABEL],
      auditoria: [ADMIN_LABEL]
    };
    var rolActual = AFO.role || '';
    NAV = NAV.filter(function (item) {
      var permitidos = ACCESO_POR_ROL[item.id];
      return !permitidos || permitidos.indexOf(rolActual) !== -1;
    });

    // Módulo activo según la ruta (las fichas y formularios heredan la sección).
    var path = window.location.pathname;
    var activo = '';
    var mejor = -1;
    NAV.forEach(function (item) {
      try {
        var base = new URL(item.href, window.location.origin).pathname;
        if (base !== '/' && path.indexOf(base) === 0 && base.length > mejor) {
          activo = item.id;
          mejor = base.length;
        }
      } catch (e) { /* ruta inválida: se ignora */ }
    });
    if (!activo && path.indexOf('/panel-general') === 0) activo = 'panel';
    if (!activo) activo = body.getAttribute('data-page') || '';

    var TITLES = {};
    NAV.forEach(function (item) { TITLES[item.id] = item.label; });

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
    var grupoActual = '';
    for (var i = 0; i < NAV.length; i++) {
      var n = NAV[i];
      if (n.group !== grupoActual) {
        grupoActual = n.group;
        navHtml += '<p class="app-nav-group-label">' + grupoActual + '</p>';
      }
      var cls = 'app-nav-item' + (n.id === activo ? ' app-nav-item-active' : '');
      var current = n.id === activo ? ' aria-current="page"' : '';
      navHtml += '<a class="' + cls + '" href="' + n.href + '"' + current + '>' +
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
          '<strong>' + (TITLES[activo] || 'Portal AFO') + '</strong>' +
        '</div>' +
        '<div class="app-topbar-actions">' +
          '<form class="app-search" id="app-search-form" role="search">' +
            '<span class="material-symbols-outlined">search</span>' +
            '<input id="app-search-input" type="search" placeholder="Buscar deportista, CI o club…" aria-label="Buscar en el padrón de deportistas"/>' +
          '</form>' +
          '<a class="app-user" href="' + (AFO.perfil || '/perfil/') + '" title="Mi perfil">' +
            '<div class="app-avatar">' + initials + '</div>' +
            '<div class="app-user-meta"><strong>' + userDisplay + '</strong><span>' + userRole + '</span></div>' +
          '</a>' +
        '</div>' +
      '</header>';

    body.prepend(shell);

    // Búsqueda global: lleva al padrón de deportistas con el término aplicado.
    var searchForm = document.getElementById('app-search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var input = document.getElementById('app-search-input');
        var termino = (input && input.value || '').trim();
        var destino = AFO.deportistas || '/deportistas/';
        window.location.href = termino
          ? destino + '?buscar=' + encodeURIComponent(termino)
          : destino;
      });
    }

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

  /* ============================================================
     Movimiento: revelado progresivo, ondas, progreso y estados.
     Cada bloque aísla sus errores para no romper la navegación.
     ============================================================ */

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) { /* navegador antiguo */ }

  function safe(fn) {
    try { fn(); } catch (e) { /* una animación nunca rompe la página */ }
  }

  function initReveals() {
    if (reduceMotion) return;
    document.documentElement.classList.add('afo-js');

    var tarjetas = Array.prototype.slice.call(
      document.querySelectorAll('main .rounded-xl, main .rounded-2xl, main .rounded-3xl')
    );

    // Solo el bloque más interno: evita animar contenedores y su contenido dos veces.
    tarjetas = tarjetas.filter(function (el) {
      if (el.hasAttribute('data-no-anim')) return false;
      if (el.closest('dialog, table, nav, header, .app-shell, .no-afo-anim, .reveal')) return false;
      if (/^(A|BUTTON|INPUT|SELECT|TEXTAREA|FORM|IMG|CANVAS|SVG|DIALOG)$/.test(el.tagName)) return false;
      if (el.querySelector('.rounded-xl, .rounded-2xl, .rounded-3xl')) return false;
      return true;
    });

    var nodos = tarjetas.slice();
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-reveal]'),
      function (el) {
        if (nodos.indexOf(el) === -1) nodos.push(el);
      }
    );

    // Escalonado por grupo de hermanos.
    var grupos = new Map();
    nodos.forEach(function (el) {
      var padre = el.parentElement;
      if (!padre) return;
      var indice = grupos.get(padre) || 0;
      grupos.set(padre, indice + 1);
      el.style.setProperty('--afo-i', String(Math.min(indice, 12)));
      el.classList.add('afo-reveal');
      // La elevación al pasar el cursor es solo para tarjetas, no para campos.
      if (tarjetas.indexOf(el) !== -1 && !el.classList.contains('afo-lift')) {
        el.classList.add('afo-lift');
      }
    });

    if (!('IntersectionObserver' in window)) {
      nodos.forEach(function (el) { el.classList.add('is-visible', 'is-settled'); });
      return;
    }

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (!entrada.isIntersecting) return;
        var el = entrada.target;
        el.classList.add('is-visible');
        observador.unobserve(el);
        var indice = parseInt(el.style.getPropertyValue('--afo-i'), 10) || 0;
        window.setTimeout(function () {
          el.classList.add('is-settled');
        }, 680 + indice * 45);
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -36px 0px' });

    nodos.forEach(function (el) { observador.observe(el); });

    // Red de seguridad: nada queda oculto si el observador no responde.
    window.setTimeout(function () {
      nodos.forEach(function (el) {
        if (el.classList.contains('is-visible')) return;
        if (el.getBoundingClientRect().top < window.innerHeight) {
          el.classList.add('is-visible', 'is-settled');
        }
      });
    }, 2400);
  }

  function initTableRows() {
    if (reduceMotion) return;
    var cuerpos = document.querySelectorAll('main table tbody');
    if (!cuerpos.length) return;

    if (!('IntersectionObserver' in window)) return;

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (!entrada.isIntersecting) return;
        Array.prototype.forEach.call(
          entrada.target.querySelectorAll('tr.afo-row'),
          function (fila) { fila.classList.add('is-visible'); }
        );
        observador.unobserve(entrada.target);
      });
    }, { threshold: 0.04 });

    Array.prototype.forEach.call(cuerpos, function (tbody) {
      Array.prototype.slice.call(tbody.rows, 0, 18).forEach(function (fila, indice) {
        fila.classList.add('afo-row');
        fila.style.setProperty('--afo-row-i', String(Math.min(indice, 14)));
      });
      observador.observe(tbody);
    });
  }

  function initRipples() {
    if (reduceMotion) return;

    document.addEventListener('pointerdown', function (evento) {
      if (evento.button !== 0) return;
      if (!evento.target || !evento.target.closest) return;

      var objetivo = evento.target.closest('a, button');
      if (!objetivo || objetivo.disabled) return;
      if (objetivo.hasAttribute('data-no-ripple')) return;

      var caja = objetivo.getBoundingClientRect();
      if (!caja.width || !caja.height) return;
      if (caja.width * caja.height > 90000) return; // tarjetas grandes: sin onda

      var tamano = Math.max(caja.width, caja.height) * 1.1;
      var onda = document.createElement('span');
      onda.className = 'afo-ripple';
      onda.style.width = tamano + 'px';
      onda.style.height = tamano + 'px';
      onda.style.left = (evento.clientX - caja.left - tamano / 2) + 'px';
      onda.style.top = (evento.clientY - caja.top - tamano / 2) + 'px';

      objetivo.classList.add('afo-rippling');
      objetivo.appendChild(onda);
      window.setTimeout(function () { onda.remove(); }, 660);
    }, { passive: true });
  }

  function initProgress() {
    var barra = document.createElement('div');
    barra.id = 'afo-progress';
    barra.setAttribute('aria-hidden', 'true');
    document.body.appendChild(barra);
    var temporizador = null;

    function terminar() {
      window.clearTimeout(temporizador);
      barra.classList.remove('is-active');
      barra.classList.add('is-done');
      window.setTimeout(function () { barra.classList.remove('is-done'); }, 540);
    }

    function comenzar() {
      window.clearTimeout(temporizador);
      barra.classList.remove('is-done');
      void barra.offsetWidth;
      barra.classList.add('is-active');
      temporizador = window.setTimeout(terminar, 15000);
    }

    window.addEventListener('pageshow', terminar);

    document.addEventListener('click', function (evento) {
      if (evento.defaultPrevented || evento.button !== 0) return;
      if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;
      if (!evento.target || !evento.target.closest) return;

      var enlace = evento.target.closest('a[href]');
      if (!enlace) return;
      if (enlace.target && enlace.target !== '_self') return;
      if (enlace.hasAttribute('download') || enlace.hasAttribute('data-no-progress')) return;

      var href = enlace.getAttribute('href') || '';
      if (!href || href.charAt(0) === '#') return;
      if (/^(mailto:|tel:|javascript:)/i.test(href)) return;

      var destino;
      try {
        destino = new URL(enlace.href, window.location.href);
      } catch (e) { return; }

      if (destino.origin !== window.location.origin) return;
      if (/\/(pdf|xlsx|csv)\/?$/.test(destino.pathname)) return; // descargas
      if (/\.(pdf|xlsx|xls|csv|zip|png|jpe?g)$/i.test(destino.pathname)) return;
      if (destino.pathname === window.location.pathname &&
          destino.search === window.location.search) return;

      comenzar();
    });

    document.addEventListener('submit', function (evento) {
      if (evento.target && evento.target.tagName === 'FORM') comenzar();
    }, true);
  }

  function initTopbarScroll() {
    var barra = document.querySelector('.app-shell-topbar');
    if (!barra) return;

    function aplicar() {
      barra.classList.toggle('is-scrolled', window.scrollY > 6);
    }

    window.addEventListener('scroll', aplicar, { passive: true });
    aplicar();
  }

  function initFieldStates() {
    document.addEventListener('focusin', function (evento) {
      var control = evento.target;
      if (!control || !control.closest) return;
      if (!/^(INPUT|SELECT|TEXTAREA)$/.test(control.tagName)) return;
      var campo = control.closest('.afo-field');
      if (campo) campo.classList.add('afo-field-focus');
    });

    document.addEventListener('focusout', function (evento) {
      var control = evento.target;
      if (!control || !control.closest) return;
      var campo = control.closest('.afo-field');
      if (campo) campo.classList.remove('afo-field-focus');
    });

    var errores = document.querySelectorAll(
      'main form .afo-field p.text-error, main form .afo-field .errorlist'
    );
    if (!errores.length) return;

    Array.prototype.forEach.call(errores, function (error) {
      var campo = error.closest('.afo-field');
      if (campo) campo.classList.add('afo-field-error');
    });

    var primero = errores[0].closest('.afo-field');
    if (!primero) return;
    window.setTimeout(function () {
      primero.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'center'
      });
    }, 340);
  }

  function iniciarMovimiento() {
    safe(initProgress);
    safe(initReveals);
    safe(initTableRows);
    safe(initRipples);
    safe(initTopbarScroll);
    safe(initFieldStates);
  }

  function iniciar() {
    safe(createShell);
    iniciarMovimiento();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
