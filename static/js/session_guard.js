/**
 * Session Guard (device security, Phase 1).
 *
 * Fallback for the realtime force-logout broadcast: periodically verifies
 * the tab's session is still alive server-side (deleted or blocked device)
 * and drops the tab to the login screen the moment it isn't.
 */
(function () {
  if (window.__vastoSessionGuard) return;
  window.__vastoSessionGuard = true;

  var PING_URL = '/users/api/security/session-alive/';
  var LOGOUT_URL = '/users/logout/';
  var INTERVAL_MS = 12000;

  function ownSessionKey() {
    var body = document.body;
    return (body && body.getAttribute('data-session-key')) || '';
  }

  function bounce(reason) {
    try { sessionStorage.setItem('vasto_forced_logout', reason || 'signed_out'); } catch (e) {}
    window.location.replace(LOGOUT_URL);
  }

  function ping() {
    // Don't ping while the tab is hidden — pick it up when it wakes.
    if (document.visibilityState === 'hidden') return;
    if (!document.cookie || document.cookie.indexOf('sessionid') === -1) return;

    try {
      var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
      var csrf = match ? decodeURIComponent(match[1]) : '';
      var body = new URLSearchParams({ session_key: ownSessionKey() });
      fetch(PING_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
        body: body
      }).then(function (res) {
        if (res.redirected || res.status === 302) { bounce('signed_out'); return; }
        return res.json().catch(function () { return { alive: true }; });
      }).then(function (data) {
        if (data && data.alive === false) {
          bounce(data.reason || 'signed_out');
        }
      }).catch(function () { /* network hiccup: ignore this round */ });
    } catch (e) { /* ignore */ }
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') ping();
  });

  function start() {
    if (document.body && document.body.getAttribute('data-session-key')) {
      setInterval(ping, INTERVAL_MS);
    } else {
      setTimeout(start, 1000);
    }
  }
  start();
})();
