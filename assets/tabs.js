// Tab bar wiring for the S.V. Mermug tracker.
//
// Owns switching between the five top-level tabs (map / voyages /
// environment / data / links). Deliberately kept separate from app.js:
// it only touches DOM visibility and layout-refresh glue, never the data
// pipeline. Panels are never removed from the DOM — only shown/hidden via
// a `.active` class — so every existing render function in app.js keeps
// targeting the same element IDs regardless of which tab is open.
(function () {
  var TAB_IDS = ['map', 'voyages', 'environment', 'data', 'links'];
  var DEFAULT_TAB = 'map';
  var STORAGE_KEY = 'mermug-active-tab';

  var tabBar = document.getElementById('tab-bar');
  var panels = document.querySelectorAll('.tab-panel');
  var buttons = document.querySelectorAll('.tab-btn');

  function isValidTab(id) {
    return TAB_IDS.indexOf(id) !== -1;
  }

  function tabFromHash() {
    var id = (window.location.hash || '').replace(/^#/, '');
    return isValidTab(id) ? id : null;
  }

  function tabFromStorage() {
    try {
      var id = localStorage.getItem(STORAGE_KEY);
      return isValidTab(id) ? id : null;
    } catch (e) {
      return null;
    }
  }

  function activateTab(tabId, opts) {
    if (!isValidTab(tabId)) tabId = DEFAULT_TAB;
    opts = opts || {};

    panels.forEach(function (panel) {
      var active = panel.dataset.tabPanel === tabId;
      panel.classList.toggle('active', active);
    });

    buttons.forEach(function (btn) {
      var active = btn.dataset.tab === tabId;
      btn.classList.toggle('active', active);
      if (active) {
        btn.setAttribute('aria-current', 'page');
      } else {
        btn.removeAttribute('aria-current');
      }
    });

    try { localStorage.setItem(STORAGE_KEY, tabId); } catch (e) {}

    if (opts.updateHash !== false && window.location.hash !== '#' + tabId) {
      history.replaceState(null, '', '#' + tabId);
    }

    // Leaflet and Chart.js both miscalculate size for anything drawn while
    // their container was `display:none`. Fix up on every switch instead
    // of touching every chart-creation call site in app.js.
    if (tabId === 'map' && window.mermugMap) {
      // Let the display:block take effect before measuring.
      requestAnimationFrame(function () { window.mermugMap.invalidateSize(); });
    }
    window.dispatchEvent(new Event('resize'));
  }

  if (tabBar) {
    tabBar.addEventListener('click', function (e) {
      var btn = e.target.closest('.tab-btn');
      if (!btn) return;
      activateTab(btn.dataset.tab);
    });
  }

  window.addEventListener('hashchange', function () {
    var id = tabFromHash();
    if (id) activateTab(id, { updateHash: false });
  });

  // Voyages tab: clicking a logged day jumps to the Map tab and zooms to
  // that day's track. renderVoyageList()/focusTrackDay() live in app.js;
  // this is just the cross-tab wiring.
  document.addEventListener('click', function (e) {
    var row = e.target.closest('.voyage-row');
    if (!row) return;
    var date = row.dataset.date;
    activateTab('map');
    if (date && typeof window.focusTrackDay === 'function') {
      window.focusTrackDay(date);
    }
  });

  activateTab(tabFromHash() || tabFromStorage() || DEFAULT_TAB, { updateHash: false });
})();
