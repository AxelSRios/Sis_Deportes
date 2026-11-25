/* ============================================================
   Sistema de Gestión Deportiva AFO · Oruro
   shell.js — shell compartido (sidebar + topbar) de navegación.

   Se activa solo en pantallas con data-shell="true". Las rutas y
   los datos del usuario llegan desde el servidor en window.AFO_URLS.
   El módulo activo se deduce de la ruta actual, de modo que listas,
   fichas y formularios resaltan su sección y abren su submenú.
   ============================================================ */
(function () {
  'use strict';

  var AFO = window.AFO_URLS || {};
  var STORAGE_COLLAPSE = 'afo-sidebar-collapsed';
  var STORAGE_OPEN = 'afo-nav-open';

  /* ------------------------------------------------------------
     Utilidades de almacenamiento seguro (modo privado / cuotas).
     ------------------------------------------------------------ */
  function leer(clave, porDefecto) {
    try {
      var valor = window.localStorage.getItem(clave);
      return valor === null ? porDefecto : valor;
    } catch (e) {
      return porDefecto;
    }
  }

  function guardar(clave, valor) {
    try { window.localStorage.setItem(clave, valor); } catch (e) { /* sin persistencia */ }
  }

  function leerLista(clave) {
    try {
      var valor = JSON.parse(leer(clave, 'null'));
      return Array.isArray(valor) ? valor : null;
    } catch (e) {
      return null;
    }
  }

  function escapar(texto) {
    return String(texto == null ? '' : texto)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /* ------------------------------------------------------------
     Estructura de navegación: cuatro áreas + cuenta.
     ------------------------------------------------------------ */
  function construirNavegacion() {
    return [
      {
        id: 'panel',
        tipo: 'enlace',
        etiqueta: 'Panel General',
        icono: 'dashboard',
        href: AFO.panel || '/panel-general/'
      },
      {
        id: 'sec-gestion',
        tipo: 'seccion',
        etiqueta: 'Gestión Deportiva',
        icono: 'sports_soccer',
        href: AFO.gestion || '/gestion-deportiva/',
        hijos: [
          { id: 'gestion', etiqueta: 'Vista general', icono: 'grid_view', href: AFO.gestion || '/gestion-deportiva/' },
          { id: 'clubes', etiqueta: 'Clubes', icono: 'shield', href: AFO.clubes || '/clubes/' },
          { id: 'canchas', etiqueta: 'Canchas', icono: 'stadium', href: AFO.canchas || '/canchas/' },
          { id: 'equipos', etiqueta: 'Equipos', icono: 'groups', href: AFO.equipos || '/equipos/' },
          { id: 'deportistas', etiqueta: 'Deportistas', icono: 'person_search', href: AFO.deportistas || '/deportistas/' },
          { id: 'categorias', etiqueta: 'Categorías', icono: 'category', href: AFO.categorias || '/categorias/' },
          { id: 'arbitros', etiqueta: 'Árbitros', icono: 'sports', href: AFO.arbitros || '/arbitros/' }
        ]
      },
      {
        id: 'sec-competencia',
        tipo: 'seccion',
        etiqueta: 'Competencia',
        icono: 'emoji_events',
        href: AFO.competencia || '/competencia/',
        hijos: [
          { id: 'competencia', etiqueta: 'Centro de torneos', icono: 'trophy', href: AFO.competencia || '/competencia/' },
          { id: 'campeonatos', etiqueta: 'Campeonatos', icono: 'emoji_events', href: AFO.campeonatos || '/campeonatos/' },
          { id: 'inscripciones', etiqueta: 'Inscripciones', icono: 'fact_check', href: AFO.inscripciones || '/inscripciones/' },
          { id: 'partidos', etiqueta: 'Partidos', icono: 'sports_soccer', href: AFO.partidos || '/partidos/' },
          { id: 'asignaciones', etiqueta: 'Asignaciones', icono: 'assignment_ind', href: AFO.asignaciones || '/asignaciones/' },
          { id: 'sanciones', etiqueta: 'Sanciones', icono: 'gavel', href: AFO.sanciones || '/sanciones/' }
        ]
      },
      {
        id: 'sec-admin',
        tipo: 'seccion',
        etiqueta: 'Administración',
        icono: 'account_balance',
        href: AFO.administracion || '/administracion/',
        hijos: [
          { id: 'administracion', etiqueta: 'Vista institucional', icono: 'space_dashboard', href: AFO.administracion || '/administracion/' },
          { id: 'tesoreria', etiqueta: 'Tesorería y pagos', icono: 'payments', href: AFO.tesoreria || '/tesoreria/' },
          { id: 'reportes', etiqueta: 'Reportes', icono: 'summarize', href: AFO.reportes || '/reportes/' },
          { id: 'usuarios', etiqueta: 'Usuarios y roles', icono: 'manage_accounts', href: AFO.usuarios || '/usuarios/' },
          { id: 'auditoria', etiqueta: 'Historial', icono: 'history', href: AFO.auditoria || '/auditoria/' },
          { id: 'accesos', etiqueta: 'Accesos y sesiones', icono: 'shield_person', href: AFO.accesos || '/accesos/' }
        ]
      }
    ];
  }

  function filtrarPorRol(nav) {
    // Accesos reservados por responsabilidad. El servidor vuelve a validar
    // el rol en cada vista (403); esto solo evita mostrar enlaces sin salida.
    var ADMIN_LABEL = 'Administrador General de la A.F.O.';
    var FINANZAS_LABEL = 'Tesorero / Finanzas Institucionales';
    var ACCESO_POR_ROL = {
      tesoreria: [ADMIN_LABEL, FINANZAS_LABEL],
      usuarios: [ADMIN_LABEL],
      auditoria: [ADMIN_LABEL],
      accesos: [ADMIN_LABEL]
    };
    var rol = AFO.role || '';

    function permitido(item) {
      var permitidos = ACCESO_POR_ROL[item.id];
      return !permitidos || permitidos.indexOf(rol) !== -1;
    }

    return nav.map(function (item) {
      if (item.tipo !== 'seccion') return item;
      var hijos = (item.hijos || []).filter(permitido);
      if (!hijos.length) return null;
      var copia = {};
      Object.keys(item).forEach(function (k) { copia[k] = item[k]; });
      copia.hijos = hijos;
      return copia;
    }).filter(Boolean);
  }

  function rutaDe(href) {
    try {
      return new URL(href, window.location.origin).pathname;
    } catch (e) {
      return '';
    }
  }

  /* ------------------------------------------------------------
     Shell: sidebar + topbar.
     ------------------------------------------------------------ */
  function createShell() {
    var body = document.body;
    if (body.getAttribute('data-shell') !== 'true') return;

    var CREST = '/static/img/afo-crest-transparent@2x.png';

    var NAV = filtrarPorRol(construirNavegacion());

    // Módulo activo según la ruta (fichas y formularios heredan la sección).
    var path = window.location.pathname;
    var activo = '';
    var mejor = -1;

    NAV.forEach(function (item) {
      var candidatos = item.tipo === 'seccion' ? item.hijos : [item];
      candidatos.forEach(function (hijo) {
        var base = rutaDe(hijo.href);
        if (base && base !== '/' && path.indexOf(base) === 0 && base.length > mejor) {
          activo = hijo.id;
          mejor = base.length;
        }
      });
    });

    if (!activo) activo = body.getAttribute('data-page') || '';

    var seccionActiva = '';
    var etiquetaActiva = '';
    NAV.forEach(function (item) {
      var candidatos = item.tipo === 'seccion' ? item.hijos : [item];
      candidatos.forEach(function (hijo) {
        if (hijo.id === activo) {
          etiquetaActiva = hijo.etiqueta;
          if (item.tipo === 'seccion') seccionActiva = item.id;
        }
      });
      if (item.tipo !== 'seccion' && item.id === activo) {
        etiquetaActiva = item.etiqueta;
      }
    });

    if (!etiquetaActiva) {
      // Último recurso: sección cuya ruta base coincide.
      NAV.forEach(function (item) {
        if (item.tipo !== 'seccion') return;
        if (path.indexOf(rutaDe(item.href)) === 0) {
          seccionActiva = item.id;
          etiquetaActiva = item.etiqueta;
        }
      });
    }

    // Estado de submenús: activo abierto; el resto recuerda la elección.
    var abiertos = leerLista(STORAGE_OPEN);
    if (!abiertos) abiertos = seccionActiva ? [seccionActiva] : [];

    var userDisplay = AFO.username || 'Administración';
    var userRole = AFO.role || 'Cómputo AFO';
    var userSafe = escapar(userDisplay);
    var roleSafe = escapar(userRole);
    var initials = userDisplay
      .trim()
      .split(/\s+/)
      .map(function (w) { return w.charAt(0); })
      .join('')
      .substring(0, 2)
      .toUpperCase();

    function enlace(hijo, esSub) {
      var cls = 'app-nav-item' + (hijo.id === activo ? ' app-nav-item-active' : '');
      var current = hijo.id === activo ? ' aria-current="page"' : '';
      var icono = esSub ? '' :
        '<span class="material-symbols-outlined app-nav-icon">' + escapar(hijo.icono) + '</span>';
      var etiqueta = escapar(hijo.etiqueta);
      return '<a class="' + cls + '" href="' + escapar(hijo.href) + '" title="' + etiqueta + '" data-tip="' + etiqueta + '"' + current + '>' +
        icono + '<span>' + etiqueta + '</span></a>';
    }

    var navHtml = '<p class="app-nav-group-label">Principal</p>';
    NAV.forEach(function (item) {
      if (item.tipo === 'enlace') {
        navHtml += enlace(item, false);
        return;
      }
      var abierto = abiertos.indexOf(item.id) !== -1;
      var activa = item.id === seccionActiva;
      navHtml +=
        '<div class="app-nav-section' + (abierto ? ' is-open' : '') + (activa ? ' is-active-section' : '') +
          '" data-section="' + item.id + '">' +
          '<button type="button" class="app-nav-section-toggle" aria-expanded="' + (abierto ? 'true' : 'false') +
            '" title="' + escapar(item.etiqueta) + '" data-tip="' + escapar(item.etiqueta) + '">' +
            '<span class="material-symbols-outlined app-nav-icon">' + escapar(item.icono) + '</span>' +
            '<span class="app-nav-section-label">' + escapar(item.etiqueta) + '</span>' +
            '<span class="material-symbols-outlined app-nav-chevron">expand_more</span>' +
          '</button>' +
          '<div class="app-nav-sub">' +
            item.hijos.map(function (hijo) { return enlace(hijo, true); }).join('') +
          '</div>' +
        '</div>';
    });

    navHtml += '<p class="app-nav-group-label">Cuenta</p>' + enlace({
      id: 'perfil',
      etiqueta: 'Mi perfil',
      icono: 'account_circle',
      href: AFO.perfil || '/perfil/'
    }, false);

    var shell = document.createElement('div');
    shell.className = 'app-shell';
    shell.innerHTML =
      '<aside class="app-shell-sidebar" id="app-sidebar" aria-label="Navegación principal">' +
        '<div class="app-sidebar-head">' +
          '<a class="app-brand" href="' + (AFO.panel || '/panel-general/') + '">' +
            '<img class="app-sidebar-crest" src="' + CREST + '" alt="Escudo de la Asociación de Fútbol Oruro"/>' +
            '<span class="app-brand-text"><strong>AFO · Oruro</strong><span>Asociación de Fútbol</span></span>' +
          '</a>' +
          '<button type="button" class="app-sidebar-collapse" id="app-collapse" aria-label="Contraer menú" title="Contraer menú">' +
            '<span class="material-symbols-outlined">chevron_left</span>' +
          '</button>' +
        '</div>' +
        '<div class="app-sidebar-season">' +
          '<span class="app-live-dot" aria-hidden="true"></span>' +
          '<span>Temporada ' + (new Date().getFullYear()) + ' · En línea</span>' +
        '</div>' +
        '<nav class="app-sidebar-nav">' + navHtml + '</nav>' +
        '<div class="app-sidebar-foot">' +
          '<div class="app-sidebar-user" title="' + userSafe + ' · ' + roleSafe + '">' +
            '<span class="app-avatar">' + escapar(initials) + '</span>' +
            '<span class="app-sidebar-user-meta"><strong>' + userSafe + '</strong><span>' + roleSafe + '</span></span>' +
          '</div>' +
          '<button type="button" class="app-sidebar-expand" id="app-expand" aria-label="Expandir menú" title="Expandir menú">' +
            '<span class="material-symbols-outlined">chevron_right</span>' +
          '</button>' +
          '<a class="app-nav-item app-nav-logout" href="' + escapar(AFO.logout || '/logout/') + '" title="Cerrar sesión">' +
            '<span class="material-symbols-outlined app-nav-icon">logout</span>' +
            '<span>Cerrar sesión</span>' +
          '</a>' +
        '</div>' +
      '</aside>' +
      '<button class="app-sidebar-backdrop" id="app-backdrop" aria-label="Cerrar menú" tabindex="-1"></button>' +
      '<header class="app-shell-topbar">' +
        '<button class="app-topbar-burger" id="app-menu-toggle" aria-label="Abrir menú" aria-controls="app-sidebar" aria-expanded="false">' +
          '<span class="material-symbols-outlined">menu</span>' +
        '</button>' +
        '<div class="app-topbar-title">' +
          '<span>' + (seccionActiva ? 'Área de gestión' : 'Consola administrativa') + '</span>' +
          '<strong>' + (etiquetaActiva || 'Portal AFO') + '</strong>' +
        '</div>' +
        '<div class="app-topbar-actions">' +
          '<button type="button" class="app-topbar-search-btn" id="app-search-toggle" aria-label="Buscar en el padrón" aria-controls="app-search-form" aria-expanded="false">' +
            '<span class="material-symbols-outlined">search</span>' +
          '</button>' +
          '<form class="app-search" id="app-search-form" role="search">' +
            '<span class="material-symbols-outlined">search</span>' +
            '<input id="app-search-input" type="search" placeholder="Buscar deportista, CI o club…" aria-label="Buscar en el padrón de deportistas" aria-keyshortcuts="/"/>' +
          '</form>' +
          '<a class="app-topbar-link" href="' + escapar(AFO.panel || '/panel-general/') + '">' +
            '<span class="material-symbols-outlined">space_dashboard</span> Panel' +
          '</a>' +
          '<a class="app-user" href="' + escapar(AFO.perfil || '/perfil/') + '" title="Mi perfil">' +
            '<div class="app-avatar">' + escapar(initials) + '</div>' +
            '<div class="app-user-meta"><strong>' + userSafe + '</strong><span>' + roleSafe + '</span></div>' +
          '</a>' +
        '</div>' +
      '</header>';

    body.prepend(shell);

    if (!document.getElementById('afo-contenido')) {
      var contenido = document.querySelector('main');
      if (contenido) contenido.id = 'afo-contenido';
    }

    // Acceso rápido al contenido para lectores de pantalla y teclado.
    var skip = document.createElement('a');
    skip.className = 'afo-skip-link';
    skip.href = '#afo-contenido';
    skip.textContent = 'Saltar al contenido';
    skip.addEventListener('click', function () {
      var destino = document.getElementById('afo-contenido');
      if (!destino) return;
      if (!destino.hasAttribute('tabindex')) destino.setAttribute('tabindex', '-1');
      window.setTimeout(function () { destino.focus({ preventScroll: true }); }, 40);
    });
    body.insertBefore(skip, body.firstChild);

    // ---------- Búsqueda global ----------
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

    // ---------- Menú móvil ----------
    var toggle = document.getElementById('app-menu-toggle');
    var backdrop = document.getElementById('app-backdrop');
    function cerrarMovil() {
      body.classList.remove('app-shell-open');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }
    if (toggle) {
      toggle.addEventListener('click', function () {
        var abierto = body.classList.toggle('app-shell-open');
        toggle.setAttribute('aria-expanded', abierto ? 'true' : 'false');
      });
    }
    if (backdrop) backdrop.addEventListener('click', cerrarMovil);
    document.addEventListener('keyup', function (e) {
      if (e.key !== 'Escape') return;
      cerrarMovil();
      cerrarBusqueda();
    });

    // ---------- Contraer / expandir sidebar ----------
    var collapse = document.getElementById('app-collapse');
    var colapsado = leer(STORAGE_COLLAPSE, '0') === '1';
    if (colapsado) body.classList.add('app-sidebar-collapsed');

    function pintarCollapse() {
      if (!collapse) return;
      var icono = collapse.querySelector('.material-symbols-outlined');
      var esta = body.classList.contains('app-sidebar-collapsed');
      if (icono) icono.textContent = esta ? 'chevron_right' : 'chevron_left';
      collapse.setAttribute('aria-label', esta ? 'Expandir menú' : 'Contraer menú');
      collapse.setAttribute('title', esta ? 'Expandir menú' : 'Contraer menú');
    }
    pintarCollapse();

    if (collapse) {
      collapse.addEventListener('click', function () {
        body.classList.toggle('app-sidebar-collapsed');
        var esta = body.classList.contains('app-sidebar-collapsed');
        guardar(STORAGE_COLLAPSE, esta ? '1' : '0');
        pintarCollapse();
      });
    }

    // Expansión desde el botón inferior del sidebar contraído.
    var expand = document.getElementById('app-expand');
    if (expand) {
      expand.addEventListener('click', function () {
        body.classList.remove('app-sidebar-collapsed');
        guardar(STORAGE_COLLAPSE, '0');
        pintarCollapse();
        var primero = document.querySelector('.app-sidebar-nav .app-nav-item');
        if (primero) primero.focus({ preventScroll: true });
      });
    }

    // ---------- Búsqueda compacta en móvil/tablet ----------
    var searchToggle = document.getElementById('app-search-toggle');
    var searchInput = document.getElementById('app-search-input');
    function cerrarBusqueda() {
      body.classList.remove('app-search-open');
      if (searchToggle) searchToggle.setAttribute('aria-expanded', 'false');
    }
    if (searchToggle) {
      searchToggle.addEventListener('click', function () {
        var abierto = body.classList.toggle('app-search-open');
        searchToggle.setAttribute('aria-expanded', abierto ? 'true' : 'false');
        if (abierto) {
          cerrarMovil();
          window.setTimeout(function () {
            if (searchInput) searchInput.focus();
          }, 60);
        }
      });
    }
    document.addEventListener('click', function (evento) {
      if (!body.classList.contains('app-search-open')) return;
      if (evento.target.closest && (evento.target.closest('.app-search') || evento.target.closest('#app-search-toggle'))) return;
      cerrarBusqueda();
    });
    if (searchForm) {
      searchForm.addEventListener('submit', function () { cerrarBusqueda(); });
    }
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1023) cerrarBusqueda();
    }, { passive: true });

    // Atajo «/» para buscar sin abandonar el teclado.
    document.addEventListener('keydown', function (evento) {
      if (evento.key !== '/' || evento.ctrlKey || evento.metaKey || evento.altKey) return;
      var objetivo = evento.target;
      if (objetivo && (objetivo.isContentEditable ||
          /^(INPUT|TEXTAREA|SELECT)$/.test(objetivo.tagName))) return;
      evento.preventDefault();
      if (window.innerWidth <= 1023) {
        body.classList.add('app-search-open');
        if (searchToggle) searchToggle.setAttribute('aria-expanded', 'true');
      }
      if (searchInput) searchInput.focus();
    });

    // ---------- Submenús de sección ----------
    Array.prototype.forEach.call(
      document.querySelectorAll('.app-nav-section'),
      function (seccion) {
        var boton = seccion.querySelector('.app-nav-section-toggle');
        if (!boton) return;
        boton.addEventListener('click', function () {
          // Si el menú está contraído, primero se expande para poder elegir.
          if (body.classList.contains('app-sidebar-collapsed')) {
            body.classList.remove('app-sidebar-collapsed');
            guardar(STORAGE_COLLAPSE, '0');
            pintarCollapse();
          }
          var abierto = seccion.classList.toggle('is-open');
          boton.setAttribute('aria-expanded', abierto ? 'true' : 'false');
          var ids = [];
          Array.prototype.forEach.call(
            document.querySelectorAll('.app-nav-section.is-open'),
            function (otra) { ids.push(otra.getAttribute('data-section')); }
          );
          guardar(STORAGE_OPEN, JSON.stringify(ids));
        });
      }
    );

    // En móvil, al elegir un destino se cierra el panel lateral.
    Array.prototype.forEach.call(
      document.querySelectorAll('.app-nav-item'),
      function (enlaceNav) {
        enlaceNav.addEventListener('click', function () {
          if (window.matchMedia('(max-width: 1023px)').matches) cerrarMovil();
        });
      }
    );
  }

  /* ============================================================
     Movimiento: contadores, revelado, ondas, progreso y estados.
     Cada bloque aísla sus errores para no romper la navegación.
     ============================================================ */

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) { /* navegador antiguo */ }

  function safe(fn) {
    try { fn(); } catch (e) { /* una animación nunca rompe la página */ }
  }

  function numero(valor) {
    if (valor === null || valor === undefined) return 0;
    var limpio = String(valor).replace(/\s/g, '').replace(/\.(?=\d{3}(\D|$))/g, '').replace(',', '.');
    var n = parseFloat(limpio);
    return isNaN(n) ? 0 : n;
  }

  function formatear(valor, decimales) {
    try {
      return Number(valor).toLocaleString('es-BO', {
        minimumFractionDigits: decimales,
        maximumFractionDigits: decimales
      });
    } catch (e) {
      return String(Math.round(valor * 100) / 100);
    }
  }

  function initCounters() {
    var nodos = document.querySelectorAll('[data-counter]');
    if (!nodos.length) return;

    function pintar(el, valor, decimales, prefijo) {
      el.textContent = prefijo + formatear(valor, decimales);
    }

    function animar(el) {
      var destino = numero(el.getAttribute('data-counter'));
      var decimales = parseInt(el.getAttribute('data-counter-decimals') || '0', 10);
      var prefijo = el.getAttribute('data-counter-prefix') || '';
      if (reduceMotion || destino === 0) {
        pintar(el, destino, decimales, prefijo);
        return;
      }
      var inicio = null;
      var duracion = 1150;
      function paso(t) {
        if (inicio === null) inicio = t;
        var avance = Math.min((t - inicio) / duracion, 1);
        var suave = 1 - Math.pow(1 - avance, 3);
        pintar(el, destino * suave, decimales, prefijo);
        if (avance < 1) window.requestAnimationFrame(paso);
        else pintar(el, destino, decimales, prefijo);
      }
      window.requestAnimationFrame(paso);
    }

    if (!('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(nodos, animar);
      return;
    }

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (!entrada.isIntersecting) return;
        animar(entrada.target);
        observador.unobserve(entrada.target);
      });
    }, { threshold: 0.25 });

    Array.prototype.forEach.call(nodos, function (el) { observador.observe(el); });

    // Red de seguridad: los contadores visibles terminan su animación.
    window.setTimeout(function () {
      Array.prototype.forEach.call(nodos, function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight) animar(el);
      });
    }, 1800);
  }

  var SELECTOR_TARJETAS = [
    'main .afo-kpi',
    'main .afo-hub',
    'main .afo-champ',
    'main .afo-match',
    'main .afo-result',
    'main .afo-module-card',
    'main .afo-chart-card',
    'main .afo-stat',
    'main .afo-fin-card',
    'main .afo-surface',
    'main .afo-card',
    'main .rounded-xl',
    'main .rounded-2xl',
    'main .rounded-3xl'
  ].join(', ');

  function initReveals() {
    if (reduceMotion) return;
    document.documentElement.classList.add('afo-js');

    var tarjetas = Array.prototype.slice.call(document.querySelectorAll(SELECTOR_TARJETAS));

    // Solo el bloque más interno: evita animar contenedores y su contenido dos veces.
    tarjetas = tarjetas.filter(function (el) {
      if (el.hasAttribute('data-no-anim')) return false;
      if (el.closest('dialog, table, nav, header, .app-shell, .no-afo-anim, .reveal')) return false;
      if (/^(A|BUTTON|INPUT|SELECT|TEXTAREA|FORM|IMG|CANVAS|SVG|DIALOG)$/.test(el.tagName)) return false;
      if (el.querySelector(SELECTOR_TARJETAS)) return false;
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
      if (!campo) return;
      campo.classList.add('afo-field-error');
      var control = campo.querySelector('input, select, textarea');
      if (control) {
        control.setAttribute('aria-invalid', 'true');
        if (!error.id) error.id = (control.id || 'campo') + '-error';
        var descrito = control.getAttribute('aria-describedby') || '';
        if (descrito.split(/\s+/).indexOf(error.id) === -1) {
          control.setAttribute('aria-describedby', (descrito ? descrito + ' ' : '') + error.id);
        }
      }
    });

    var primero = errores[0].closest('.afo-field');
    if (!primero) return;

    // Al volver con errores, la planilla debe verse completa de inmediato.
    var tarjeta = primero.closest('.afo-form-card');
    if (tarjeta) {
      Array.prototype.forEach.call(
        tarjeta.querySelectorAll('.afo-reveal, [data-reveal]'),
        function (el) { el.classList.add('is-visible', 'is-settled'); }
      );
    }

    window.setTimeout(function () {
      var resumen = document.querySelector('.afo-form-error-summary');
      if (resumen) resumen.setAttribute('tabindex', '-1');
      (resumen || primero).scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: resumen ? 'start' : 'center'
      });
      if (resumen) {
        try { resumen.focus({ preventScroll: true }); } catch (e) { /* navegador antiguo */ }
        return;
      }
      var control = primero.querySelector('input, select, textarea');
      if (control) {
        try { control.focus({ preventScroll: true }); } catch (e) { /* navegador antiguo */ }
      }
    }, 340);
  }

  /* ------------------------------------------------------------
     Tablas adaptables: en pantallas estrechas cada fila se
     presenta como ficha con la etiqueta de su columna.
     ------------------------------------------------------------ */
  function initResponsiveTables() {
    var tablas = document.querySelectorAll('main table');
    if (!tablas.length) return;

    Array.prototype.forEach.call(tablas, function (tabla) {
      if (tabla.closest('dialog')) return;
      var encabezados = Array.prototype.map.call(
        tabla.querySelectorAll('thead th'),
        function (th) { return (th.textContent || '').replace(/\s+/g, ' ').trim(); }
      );
      if (!encabezados.length) return;

      tabla.classList.add('afo-table-stack');
      var contenedor = tabla.closest('.overflow-x-auto');
      if (contenedor) contenedor.classList.add('afo-table-stack-wrap');

      Array.prototype.forEach.call(tabla.querySelectorAll('tbody tr'), function (fila) {
        Array.prototype.forEach.call(fila.children, function (celda, indice) {
          if (celda.tagName !== 'TD') return;
          if (celda.hasAttribute('colspan')) return;
          if (!celda.hasAttribute('data-label') && encabezados[indice]) {
            celda.setAttribute('data-label', encabezados[indice]);
          }
        });
      });
    });
  }

  /* ------------------------------------------------------------
     Avisos: cierre manual accesible y salida suave.
     ------------------------------------------------------------ */
  function initFlashMessages() {
    var avisos = document.querySelectorAll('main .afo-flash');
    Array.prototype.forEach.call(avisos, function (aviso) {
      if (aviso.querySelector('.afo-flash-close')) return;
      var boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'afo-flash-close';
      boton.setAttribute('aria-label', 'Cerrar aviso');
      boton.innerHTML = '<span class="material-symbols-outlined">close</span>';
      boton.addEventListener('click', function () {
        aviso.classList.add('is-hiding');
        window.setTimeout(function () { aviso.remove(); }, 240);
      });
      aviso.appendChild(boton);
    });
  }

  function iniciarMovimiento() {
    safe(initProgress);
    safe(initCounters);
    safe(initReveals);
    safe(initTableRows);
    safe(initRipples);
    safe(initTopbarScroll);
    safe(initFieldStates);
    safe(initResponsiveTables);
    safe(initFlashMessages);
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
