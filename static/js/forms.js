/* ============================================================
   Sistema de Gestión Deportiva AFO · Oruro
   forms.js — planillas de registro modernas.

   Añade a los formularios marcados con data-afo-form:
   - Progreso de campos obligatorios completados.
   - Estado «cambios sin guardar» y aviso al salir.
   - Estado de guardado en el botón de envío.
   Sin JavaScript el formulario sigue funcionando igual.
   ============================================================ */
(function () {
  'use strict';

  function inicializar(form) {
    var tarjeta = form.querySelector('[data-form-card]') || form;
    var chip = form.querySelector('[data-form-dirty]');
    var envolturaProgreso = form.querySelector('[data-form-progress-wrap]');
    var barraProgreso = form.querySelector('[data-form-progress]');
    var etiquetaProgreso = form.querySelector('[data-form-progress-label]');
    var conteoProgreso = form.querySelector('[data-form-progress-count]');
    var boton = form.querySelector('[data-form-submit]');
    var iconoBoton = boton ? boton.querySelector('[data-submit-icon]') : null;
    var textoBoton = boton ? boton.querySelector('[data-submit-label]') : null;
    var textoOriginal = textoBoton ? textoBoton.textContent : '';
    var iconoOriginal = iconoBoton ? iconoBoton.textContent : '';

    var controles = Array.prototype.slice.call(
      form.querySelectorAll('input, select, textarea')
    ).filter(function (control) {
      var tipo = (control.getAttribute('type') || '').toLowerCase();
      return tipo !== 'hidden' && tipo !== 'submit' && tipo !== 'button';
    });

    var obligatorios = controles.filter(function (control) {
      return control.required;
    });

    function instantanea() {
      try {
        return new URLSearchParams(new FormData(form)).toString();
      } catch (e) {
        return '';
      }
    }

    var estadoInicial = instantanea();
    var enviando = false;

    function estaCompleto(control) {
      var tipo = (control.getAttribute('type') || '').toLowerCase();
      if (tipo === 'checkbox' || tipo === 'radio') return control.checked;
      return String(control.value || '').trim() !== '';
    }

    function actualizarProgreso() {
      if (!envolturaProgreso || !obligatorios.length) {
        if (envolturaProgreso) envolturaProgreso.classList.add('hidden');
        return;
      }

      var completos = obligatorios.filter(estaCompleto).length;
      var porcentaje = Math.round((completos / obligatorios.length) * 100);

      if (barraProgreso) {
        barraProgreso.style.width = porcentaje + '%';
        barraProgreso.classList.toggle('is-complete', porcentaje === 100);
      }
      if (etiquetaProgreso) etiquetaProgreso.textContent = porcentaje + '%';
      if (conteoProgreso) {
        conteoProgreso.textContent = completos + ' de ' + obligatorios.length;
      }
    }

    function actualizarEstado() {
      var cambiado = instantanea() !== estadoInicial;
      tarjeta.classList.toggle('is-dirty', cambiado);
      if (chip) chip.setAttribute('aria-hidden', cambiado ? 'false' : 'true');
      return cambiado;
    }

    function refrescar() {
      actualizarProgreso();
      actualizarEstado();
    }

    controles.forEach(function (control) {
      control.addEventListener('input', refrescar);
      control.addEventListener('change', refrescar);
    });

    form.addEventListener('reset', function () {
      window.setTimeout(refrescar, 0);
    });

    form.addEventListener('submit', function () {
      enviando = true;
      actualizarEstado();

      if (boton && !boton.disabled) {
        boton.disabled = true;
        boton.classList.add('afo-submit', 'is-loading');
        boton.setAttribute('aria-busy', 'true');
        if (iconoBoton) iconoBoton.textContent = 'progress_activity';
        if (textoBoton) textoBoton.textContent = 'Guardando…';
      }
    });

    window.addEventListener('beforeunload', function (evento) {
      if (enviando) return;
      if (instantanea() === estadoInicial) return;
      evento.preventDefault();
      evento.returnValue = '';
      return '';
    });

    // Al volver con el botón «atrás», el navegador puede restaurar valores.
    window.addEventListener('pageshow', function () {
      if (enviando && boton) {
        enviando = false;
        boton.disabled = false;
        boton.classList.remove('afo-submit', 'is-loading');
        boton.removeAttribute('aria-busy');
        if (iconoBoton) iconoBoton.textContent = iconoOriginal;
        if (textoBoton) textoBoton.textContent = textoOriginal;
      }
      refrescar();
    });

    refrescar();
  }

  function iniciar() {
    Array.prototype.forEach.call(
      document.querySelectorAll('form[data-afo-form]'),
      function (form) {
        try { inicializar(form); } catch (e) { /* sin JS el formulario sigue igual */ }
      }
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
