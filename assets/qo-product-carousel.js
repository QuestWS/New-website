(function () {
  function init(root) {
    if (root.dataset.qoReady) return;
    root.dataset.qoReady = '1';
    var track = root.querySelector('[data-qo-track]');
    var prev = root.querySelector('[data-qo-prev]');
    var next = root.querySelector('[data-qo-next]');
    if (!track) return;
    function step() {
      var card = track.querySelector('li');
      return card ? (card.getBoundingClientRect().width + 16) * (window.innerWidth >= 750 ? 2 : 1) : track.clientWidth;
    }
    function update() {
      if (!prev || !next) return;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
    }
    if (prev) prev.addEventListener('click', function () { track.scrollBy({ left: -step(), behavior: 'smooth' }); });
    if (next) next.addEventListener('click', function () { track.scrollBy({ left: step(), behavior: 'smooth' }); });
    track.addEventListener('scroll', function () { window.requestAnimationFrame(update); }, { passive: true });
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { track.scrollBy({ left: step(), behavior: 'smooth' }); }
      if (e.key === 'ArrowLeft') { track.scrollBy({ left: -step(), behavior: 'smooth' }); }
    });
    window.addEventListener('resize', update);
    update();
  }
  function initAll() { document.querySelectorAll('[data-qo-carousel]').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll); else initAll();
  document.addEventListener('shopify:section:load', initAll);
})();
