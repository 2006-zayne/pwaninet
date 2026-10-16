/* Shared start-conversation handler: rail + modal + profile + cards.
 * Single delegated listener (capture) so inline duplicates can't break it.
 * POSTs /messaging/v1/conversations/ {type:'direct', member_ids:[int]} then navigates.
 */
(function () {
  if (window.__pwaniStartConvGlobalBound) return;
  window.__pwaniStartConvGlobalBound = true;

  function getCSRF() {
    const m = document.querySelector('meta[name="csrf-token"]');
    if (m && m.content) return m.content;
    const i = document.querySelector('[name=csrfmiddlewaretoken]');
    if (i && i.value) return i.value;
    const c = (document.cookie || '').split('; ').find(function (r) { return r.indexOf('csrftoken=') === 0; });
    return c ? c.split('=')[1] : '';
  }

  function navigate(convId) {
    window.location.href = '/messaging/conversation/' + convId + '/';
  }

  document.addEventListener('click', function (e) {
    const btn = e.target && e.target.closest
      ? e.target.closest('.start-conversation, .start-conversation-btn, .profile-message-btn')
      : null;
    if (!btn) return;
    // Ignore Add-Friend buttons that share card styles but have no message intent
    if (btn.dataset && btn.dataset.action === 'follow') return;

    e.preventDefault();
    e.stopPropagation();
    if (typeof e.stopImmediatePropagation === 'function') {
      try { e.stopImmediatePropagation(); } catch (_) {}
    }

    const userId = btn.dataset ? btn.dataset.userId : null;
    if (!userId) return;
    if (btn.dataset.conversationId) {
      navigate(btn.dataset.conversationId);
      return;
    }
    if (btn.dataset.busy === '1') return;
    btn.dataset.busy = '1';
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.innerHTML = 'Opening...';

    fetch('/messaging/v1/conversations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
      body: JSON.stringify({ type: 'direct', member_ids: [parseInt(userId, 10)] })
    })
      .then(function (r) {
        if (!r.ok) return r.text().then(function (t) { throw new Error('HTTP ' + r.status + ': ' + (t || '').slice(0, 300)); });
        return r.json();
      })
      .then(function (data) {
        const convId = data && (data.id || data.conversation_id);
        if (convId) { navigate(convId); return; }
        if (data && data.redirect_url) { window.location.href = data.redirect_url; return; }
        throw new Error('No conversation ID in response');
      })
      .catch(function (err) {
        console.error('[start-conversation] failed:', err);
        btn.dataset.busy = '';
        btn.disabled = false;
        btn.innerHTML = orig;
        alert('Could not open conversation: ' + (err && err.message ? err.message : err));
      });
  }, true);
})();
