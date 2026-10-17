(function () {
  var TZ = 'America/Chicago';
  function chicagoToday() {
    var p = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: 'numeric', day: 'numeric' }).formatToParts(new Date());
    var o = {};
    p.forEach(function (x) { o[x.type] = parseInt(x.value, 10); });
    return o;
  }
  function nthMonday(y, m, last, n) {
    var first = new Date(Date.UTC(y, m - 1, 1)).getUTCDay();
    var firstMon = 1 + ((8 - first) % 7);
    if (!last) return firstMon + 7 * (n - 1);
    var dim = new Date(Date.UTC(y, m, 0)).getUTCDate();
    var d = firstMon;
    while (d + 7 <= dim) d += 7;
    return d;
  }
  function currentSeason() {
    var t = chicagoToday(), y = t.year, md = t.month * 100 + t.day;
    var memorial = 500 + nthMonday(y, 5, true);
    var labor = 900 + nthMonday(y, 9, false, 1);
    if (md >= 401 && md < memorial) return 'spring';
    if (md >= memorial && md < labor) return 'summer';
    if (md >= labor && md <= 1031) return 'fall';
    return 'winter';
  }
  function init(list) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;
    function panel(tab) { return document.getElementById(tab.getAttribute('aria-controls')); }
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        var p = panel(t);
        if (p) p.hidden = !on;
      });
      if (focus) tab.focus();
    }
    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { select(tab); });
      tab.addEventListener('keydown', function (e) {
        var n = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') n = tabs[(i + 1) % tabs.length];
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') n = tabs[(i - 1 + tabs.length) % tabs.length];
        else if (e.key === 'Home') n = tabs[0];
        else if (e.key === 'End') n = tabs[tabs.length - 1];
        if (n) { e.preventDefault(); select(n, true); }
      });
    });
    var now = currentSeason();
    var match = tabs.filter(function (t) { return t.getAttribute('data-season') === now; })[0];
    select(match || tabs[0]);
  }
  function run() {
    document.querySelectorAll('[data-qo-tabs]').forEach(init);
    var s = document.getElementById('QuestFooterContactStatus');
    if (s && location.hash === '#QuestFooterContact') { try { s.focus({ preventScroll: true }); } catch (e) {} }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
