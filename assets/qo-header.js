(function () {
  var header = document.querySelector('[data-qo-header]');
  if (!header) return;
  var panel = header.querySelector('.qo-panel');
  var openBtn = header.querySelector('[data-qo-open]');
  var closeBtn = header.querySelector('[data-qo-close]');
  var mq = window.matchMedia('(min-width: 990px)');
  var lastFocus = null;

  /* Desktop dropdowns: keyboard toggle buttons, focus, Escape */
  var parents = header.querySelectorAll('.qo-nav__item--parent');
  function closeAll(except) {
    parents.forEach(function (li) {
      if (li !== except) {
        li.classList.remove('is-open');
        var b = li.querySelector('.qo-nav__toggle');
        if (b) b.setAttribute('aria-expanded', 'false');
      }
    });
  }
  parents.forEach(function (li) {
    var btn = li.querySelector('.qo-nav__toggle');
    li.addEventListener('focusin', function () { closeAll(li); li.classList.add('is-open'); if (btn) btn.setAttribute('aria-expanded', 'true'); });
    li.addEventListener('mouseenter', function () { closeAll(li); });
    li.addEventListener('focusout', function (e) {
      if (!li.contains(e.relatedTarget)) { li.classList.remove('is-open'); if (btn) btn.setAttribute('aria-expanded', 'false'); }
    });
    if (btn) btn.addEventListener('click', function () {
      var o = li.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', o ? 'true' : 'false');
    });
  });
  header.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open = header.querySelector('.qo-nav__item.is-open');
    if (open) { var a = open.querySelector('.qo-nav__link'); closeAll(); if (a) a.focus(); if (document.activeElement) document.activeElement.blur(); if (a) a.focus(); }
  });

  /* Mobile panel */
  function focusables() {
    return Array.prototype.filter.call(panel.querySelectorAll('a[href], button, input'), function (el) { return el.offsetParent !== null; });
  }
  function openPanel() {
    lastFocus = document.activeElement;
    panel.hidden = false;
    panel.getBoundingClientRect();
    panel.classList.add('is-open');
    document.body.classList.add('qo-menu-open');
    openBtn.setAttribute('aria-expanded', 'true');
    setTimeout(function () { closeBtn.focus(); }, 50);
  }
  function closePanel() {
    panel.classList.remove('is-open');
    document.body.classList.remove('qo-menu-open');
    openBtn.setAttribute('aria-expanded', 'false');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  if (openBtn) openBtn.addEventListener('click', openPanel);
  if (closeBtn) closeBtn.addEventListener('click', closePanel);
  panel.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closePanel(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables();
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  panel.querySelectorAll('.qo-pnav__toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var sub = btn.closest('.qo-pnav__item').querySelector('.qo-pnav__sub');
      var o = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', o ? 'false' : 'true');
      if (sub) sub.hidden = o;
    });
  });
  var onChange = function () { if (mq.matches && panel.classList.contains('is-open')) closePanel(); };
  if (mq.addEventListener) mq.addEventListener('change', onChange); else mq.addListener(onChange);
})();
