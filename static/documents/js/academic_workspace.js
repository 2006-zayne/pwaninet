/*
  VASTO Student Dashboard — workspace interactions.
  Scope: left-rail collapse (persisted), context-rail close/reopen (persisted,
  bottom-sheet on mobile), Units/Cohort tabs, section-nav active sync after
  HTMX swaps, theme tri-toggle sync over base.html's global setTheme(),
  mobile day tabs, and cross-section openers (Add Slot / Upload timetable).
*/
(function () {
  'use strict';

  var isMobile = function () { return window.innerWidth < 992; };

  /* ── Left rail collapse (persisted) ─────────────────────────────────── */
  window.vdwToggleLeft = function () {
    var collapsed = !document.body.classList.contains('vdw-left-collapsed');
    document.body.classList.toggle('vdw-left-collapsed', collapsed);
    try { localStorage.setItem('vdw_left_collapsed', collapsed ? '1' : '0'); } catch (e) {}
  };

  /* ── Context rail: close / reopen (persisted on desktop) ────────────── */
  var backdrop = function () { return document.getElementById('vdwSheetBackdrop'); };
  var syncSheet = function () {
    var el = backdrop();
    if (el) el.classList.toggle('open', isMobile() && document.body.classList.contains('vdw-ctx-open'));
  };

  window.vdwToggleCtx = function () {
    if (isMobile()) {
      var open = document.body.classList.contains('vdw-ctx-open');
      document.body.classList.toggle('vdw-ctx-open', !open);
      document.body.classList.remove('vdw-ctx-collapsed');
      syncSheet();
      return;
    }
    var collapsed = !document.body.classList.contains('vdw-ctx-collapsed');
    document.body.classList.toggle('vdw-ctx-collapsed', collapsed);
    try { localStorage.setItem('vdw_ctx_collapsed', collapsed ? '1' : '0'); } catch (e) {}
  };

  window.vdwCloseCtx = function () {
    if (isMobile()) {
      document.body.classList.remove('vdw-ctx-open');
      syncSheet();
    } else {
      document.body.classList.add('vdw-ctx-collapsed');
      try { localStorage.setItem('vdw_ctx_collapsed', '1'); } catch (e) {}
    }
  };

  /* ── Theme quick-cycle: light → dark → system (syncs base's setTheme) ── */
  var THEME_ICONS = { light: 'bi-sun-fill', dark: 'bi-moon-stars-fill', system: 'bi-circle-half' };
  window.vdwThemeCycle = function () {
    var pref = 'system';
    try { pref = localStorage.getItem(THEME_STORAGE_KEY) || 'system'; } catch (e) {}
    var next = pref === 'system' ? 'light' : (pref === 'light' ? 'dark' : 'system');
    if (typeof window.setTheme === 'function') window.setTheme(next, true);
    window.vdwSyncThemeBtns();
  };

  /* ── Theme tri-toggle sync (over base.html's global setTheme) ───────── */
  var THEME_STORAGE_KEY = 'theme';
  window.vdwSyncThemeBtns = function () {
    var pref = 'system';
    try { pref = localStorage.getItem(THEME_STORAGE_KEY) || 'system'; } catch (e) {}
    document.querySelectorAll('.vdw-theme-btn').forEach(function (btn) {
      btn.classList.toggle('on', (btn.dataset.vdwTheme || '') === pref);
    });
    // Mobile quick-cycle button mirrors the active preference with its icon.
    var mob = document.getElementById('vdwMobThemeBtn');
    if (mob) {
      var icon = mob.querySelector('i');
      if (icon) icon.className = 'bi ' + (THEME_ICONS[pref] || THEME_ICONS.system);
      mob.title = 'Theme: ' + pref + ' (tap to change)';
    }
  };

  /* ── Section nav active-state sync across rail + bottom nav ─────────── */
  var syncSection = function (section) {
    document.querySelectorAll('[data-vdw-nav]').forEach(function (el) {
      el.classList.toggle('active', el.dataset.vdwNav === section);
    });
  };

  /* ── Units/Cohort tabs (client-side states inside #ctx-body) ────────── */
  var ctxTab = 'units';
  var applyCtxTab = function () {
    document.querySelectorAll('#ctx-body [data-ctx-state]').forEach(function (state) {
      state.classList.toggle('on', state.dataset.ctxState === ctxTab);
    });
    document.querySelectorAll('#vdwCtx [data-ctx-tab]').forEach(function (tab) {
      tab.classList.toggle('active', tab.dataset.ctxTab === ctxTab);
    });
  };
  window.vdwSetCtxTab = function (tab) { ctxTab = tab; applyCtxTab(); };

  /* ── HTMX lifecycle wiring ───────────────────────────────────────────── */
  document.body.addEventListener('htmx:beforeSwap', function () {
    if (!document.getElementById('vdwLoadingBar')) {
      var bar = document.createElement('div');
      bar.id = 'vdwLoadingBar';
      bar.className = 'vdw-loading';
      document.body.appendChild(bar);
    }
  });
  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var bar = document.getElementById('vdwLoadingBar');
    if (bar) bar.remove();

    if (!evt || !evt.target) return;

    // Centre swapped → sync section highlight + pending openers.
    if (evt.target.id === 'dash-main') {
      var root = document.querySelector('#dash-main [data-vdw-section]');
      if (root) {
        syncSection(root.dataset.vdwSection);
        // Pending cross-section openers (rail Add-Slot / camera from another section)
        if (root.dataset.vdwSection === 'timetable') {
          if (window.vdwPendingAddSlot) {
            window.vdwPendingAddSlot = false;
            var drawer = document.getElementById('timetable-add-slot-drawer');
            if (drawer) drawer.style.display = 'block';
          }
          if (window.vdwPendingUpload) {
            window.vdwPendingUpload = false;
            if (typeof window.triggerTimetableUpload === 'function') window.triggerTimetableUpload();
          }
        }
      }
    }

    // Context body swapped (OOB or partial) → keep the active tab applied.
    if (evt.target.id === 'ctx-body' || (evt.detail && evt.detail.target && evt.detail.target.id === 'ctx-body')) {
      ctxTab = ctxTab || 'units';
      applyCtxTab();
    }
  });

  /* ── Fullscreen landscape timetable overlay (mobile) ─────────────────── */
  var ttOverlay = function () { return document.getElementById('vdwTtOverlay'); };
  var ttHolder = function () { return document.getElementById('vdwTtOverlayGrid'); };
  var lastOverlayTap = 0;

  window.vdwOpenTtOverlay = function () {
    var ov = ttOverlay(), holder = ttHolder();
    var grid = document.querySelector('#dash-main .vdw-week-grid');
    if (!ov || !holder || !grid) return;
    holder.innerHTML = '';
    holder.appendChild(grid.cloneNode(true));
    document.body.classList.add('vdw-overlay-open');
    ov.classList.add('open');
    ov.setAttribute('aria-hidden', 'false');
    lastOverlayTap = 0;
  };

  window.vdwCloseTtOverlay = function () {
    var ov = ttOverlay();
    if (!ov) return;
    ov.classList.remove('open');
    ov.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('vdw-overlay-open');
  };

  window.addEventListener('load', function () {
    vdwSyncThemeBtns();
    applyCtxTab();
    syncSection(document.querySelector('#dash-main [data-vdw-section]')?.dataset.vdwSection || 'timetable');
    // Remove base-shell chrome that ships with inline !important styles.
    ['twoFactorNudgeBanner', 'vasto-install-banner', 'back-to-top-btn'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.remove();
    });
  });

  // Tap the fitted timetable card (mobile) → open the overlay.
  document.addEventListener('click', function (evt) {
    if (window.innerWidth >= 992) return;
    if (evt.target.closest('#vdwTtOverlay')) {
      // Double-tap closes; single tap leaves scrolling free.
      var now = Date.now();
      if (now - lastOverlayTap < 320 && !evt.target.closest('.vdw-slot-delete')) {
        evt.preventDefault();
        lastOverlayTap = 0;
        window.vdwCloseTtOverlay();
        return;
      }
      lastOverlayTap = now;
      return;
    }
    if (evt.target.closest('.vdw-grid-scroll') && !evt.target.closest('.vdw-slot-delete')) {
      window.vdwOpenTtOverlay();
    }
  });
  document.addEventListener('keydown', function (evt) {
    if (evt.key === 'Escape') window.vdwCloseTtOverlay();
  });

  /* ── Cross-section openers ───────────────────────────────────────────── */
  window.vdwOpenAddSlot = function () {
    var drawer = document.getElementById('timetable-add-slot-drawer');
    if (drawer) { drawer.style.display = 'block'; return; }
    window.vdwPendingAddSlot = true;
    var url = (document.body.dataset.vdwTtUrl || '');
    if (url && window.htmx) htmx.ajax('GET', url, { target: '#dash-main', swap: 'innerHTML' });
  };

  window.vdwOpenUpload = function () {
    if (typeof window.triggerTimetableUpload === 'function' &&
        document.getElementById('timetableImageFileInput')) {
      window.triggerTimetableUpload();
      return;
    }
    window.vdwPendingUpload = true;
    var url = (document.body.dataset.vdwTtUrl || '');
    if (url && window.htmx) htmx.ajax('GET', url, { target: '#dash-main', swap: 'innerHTML' });
  };
})();
