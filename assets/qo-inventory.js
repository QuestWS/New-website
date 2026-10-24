/* Quest Watersports inventory: product gallery + request button, and client-side grid filtering */
(function () {
  'use strict';

  /* ---------- Product gallery ---------- */
  function initGallery(root) {
    var track = root.querySelector('[data-gal-track]');
    if (!track) return;
    var slides = track.querySelectorAll('[data-gal-slide]');
    var thumbs = root.querySelectorAll('[data-gal-thumb]');
    var cur = root.querySelector('[data-gal-current]');
    var index = 0;
    function go(i) {
      i = Math.max(0, Math.min(slides.length - 1, i));
      track.scrollTo({ left: slides[i].offsetLeft - track.offsetLeft, behavior: 'smooth' });
    }
    function setActive(i) {
      if (i === index) return;
      index = i;
      if (cur) cur.textContent = String(i + 1);
      thumbs.forEach(function (t, n) { t.classList.toggle('is-active', n === i); });
      var t = thumbs[i];
      if (t && t.parentNode && t.parentNode.parentNode) {
        var box = t.parentNode.parentNode;
        box.scrollTo({ left: t.offsetLeft - box.clientWidth / 2 + t.clientWidth / 2, behavior: 'smooth' });
      }
    }
    var raf;
    track.addEventListener('scroll', function () {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () { setActive(Math.round(track.scrollLeft / track.clientWidth)); });
    }, { passive: true });
    var p = root.querySelector('[data-gal-prev]'), n = root.querySelector('[data-gal-next]');
    if (p) p.addEventListener('click', function () { go(index - 1); });
    if (n) n.addEventListener('click', function () { go(index + 1); });
    thumbs.forEach(function (t) { t.addEventListener('click', function () { go(Number(t.dataset.galThumb)); }); });
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { go(index - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { go(index + 1); e.preventDefault(); }
    });
    var page = root.closest('[data-qo-inv]') || document;
    var lb = page.querySelector('[data-qo-lightbox]');
    if (lb && typeof lb.showModal === 'function') {
      var img = lb.querySelector('[data-lb-img]');
      root.querySelectorAll('[data-gal-zoom]').forEach(function (b) {
        b.addEventListener('click', function () { img.src = b.dataset.galZoom; lb.showModal(); });
      });
      lb.addEventListener('click', function () { lb.close(); });
    }
  }

  document.querySelectorAll('[data-qo-gallery]').forEach(initGallery);

  document.querySelectorAll('[data-qo-request]').forEach(function (a) {
    a.addEventListener('click', function () {
      var target = document.getElementById('qo-request-info');
      if (!target) return;
      setTimeout(function () {
        var f = target.querySelector('input[name="contact[name]"]');
        if (f) f.focus({ preventScroll: true });
      }, 450);
    });
  });

  /* ---------- Inventory grid filters ---------- */
  document.querySelectorAll('[data-qo-invgrid]').forEach(function (root) {
    var cards = Array.prototype.slice.call(root.querySelectorAll('[data-card]'));
    var list = root.querySelector('[data-list]');
    var q = root.querySelector('[data-f="q"]');
    var sel = {
      type: root.querySelector('[data-f="type"]'),
      make: root.querySelector('[data-f="make"]'),
      cond: root.querySelector('[data-f="cond"]'),
      sort: root.querySelector('[data-f="sort"]')
    };
    var count = root.querySelector('[data-count]');
    var empty = root.querySelector('[data-empty]');
    var bar = root.querySelector('.qo-fbar');
    var toggle = root.querySelector('[data-toggle]');
    var reset = root.querySelector('[data-reset]');
    var original = cards.slice();

    function fill(select, key) {
      if (!select) return;
      var vals = {};
      cards.forEach(function (c) { var v = c.dataset[key]; if (v) vals[v] = true; });
      Object.keys(vals).sort(function (a, b) { return a.localeCompare(b); }).forEach(function (v) {
        var o = document.createElement('option'); o.value = v; o.textContent = v; select.appendChild(o);
      });
    }
    fill(sel.type, 'type'); fill(sel.make, 'make');

    var params = new URLSearchParams(location.search);
    function preset(el, name) { if (el && params.get(name)) { el.value = params.get(name); } }
    preset(sel.type, 'type'); preset(sel.make, 'make'); preset(sel.cond, 'condition'); preset(q, 'q');

    function apply() {
      var term = (q && q.value || '').trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (c) {
        var ok = (!sel.type.value || c.dataset.type === sel.type.value) &&
                 (!sel.make.value || c.dataset.make === sel.make.value) &&
                 (!sel.cond.value || c.dataset.cond === sel.cond.value) &&
                 (!term || c.dataset.search.indexOf(term) !== -1);
        c.hidden = !ok;
        if (ok) shown++;
      });
      var s = sel.sort.value;
      var sorted = original.slice();
      if (s === 'price-asc' || s === 'price-desc') {
        sorted.sort(function (a, b) {
          var pa = Number(a.dataset.price) || 0, pb = Number(b.dataset.price) || 0;
          if (!pa && pb) return 1; if (pa && !pb) return -1; /* call-for-price last */
          return s === 'price-asc' ? pa - pb : pb - pa;
        });
      } else if (s === 'year-desc' || s === 'year-asc') {
        sorted.sort(function (a, b) {
          var ya = Number(a.dataset.year) || 0, yb = Number(b.dataset.year) || 0;
          return s === 'year-desc' ? yb - ya : ya - yb;
        });
      }
      sorted.forEach(function (c) { list.appendChild(c); });
      if (count) count.textContent = shown + (shown === 1 ? ' unit' : ' units');
      if (empty) empty.hidden = shown !== 0;
    }
    ['type', 'make', 'cond', 'sort'].forEach(function (k) { sel[k].addEventListener('change', apply); });
    if (q) {
      var t; q.addEventListener('input', function () { clearTimeout(t); t = setTimeout(apply, 120); });
      q.addEventListener('keydown', function (e) { if (e.key === 'Enter') e.preventDefault(); });
    }
    if (reset) reset.addEventListener('click', function () {
      ['type', 'make', 'cond'].forEach(function (k) { sel[k].value = ''; });
      sel.sort.value = ''; if (q) q.value = ''; apply();
    });
    if (toggle) toggle.addEventListener('click', function () {
      var open = bar.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    apply();
  });
})();
