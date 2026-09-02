/**
 * Profile Architecture JS Manager
 * Idempotently handles profile image preloading, collapse buttons, people modal triggers,
 * completion card dismissal, and floating action button scroll behavior.
 */

(function () {
  'use strict';

  function initProfilePage() {
    const profileContent = document.querySelector('.profile-content');

    // Clean up scroll handler if not on profile page
    if (!profileContent) {
      if (window._floatingButtonScrollHandler) {
        window.removeEventListener('scroll', window._floatingButtonScrollHandler);
        window._floatingButtonScrollHandler = null;
      }
      return;
    }

    // 1. Preload Critical Images & Avatar Loaded State
    const coverContainer = profileContent.querySelector('.cover-container');
    if (coverContainer) {
      const bgUrl = coverContainer.getAttribute('data-bg-url');
      if (bgUrl) {
        const img = new Image();
        img.onload = function () {
          coverContainer.style.backgroundImage = `url('${bgUrl}')`;
        };
        img.src = bgUrl;
      }
    }

    const avatarImages = profileContent.querySelectorAll('.avatar');
    avatarImages.forEach((img) => {
      img.classList.add('loaded');
      if (!img.complete) {
        img.addEventListener('load', function () {
          img.classList.add('loaded');
        });
      }
    });

    // 2. Floating Documents Button Scroll Behavior
    const documentsBtn = document.getElementById('documents-btn');
    if (documentsBtn) {
      let lastScrollTop = 0;
      const scrollThreshold = 100;

      if (window._floatingButtonScrollHandler) {
        window.removeEventListener('scroll', window._floatingButtonScrollHandler);
      }

      window._floatingButtonScrollHandler = function () {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const btn = document.getElementById('documents-btn');
        if (btn) {
          if (scrollTop > lastScrollTop && scrollTop > scrollThreshold) {
            btn.classList.add('hidden');
          } else if (scrollTop < lastScrollTop - 50) {
            btn.classList.remove('hidden');
          }
        }
        lastScrollTop = scrollTop;
      };

      window.addEventListener('scroll', window._floatingButtonScrollHandler);

      // Remove initial animation after 5.2s
      setTimeout(() => {
        const btn = document.getElementById('documents-btn');
        if (btn) {
          btn.classList.remove('initial-animation');
        }
      }, 5200);
    }

    // 3. View More About Collapse Button
    const viewMoreBtn = document.getElementById('profileViewMoreBtn');
    const profileMoreInfo = document.getElementById('profileMoreInfo');

    function setViewMoreExpanded(expanded) {
      if (!viewMoreBtn) return;
      const icon = viewMoreBtn.querySelector('.view-more-icon');
      const text = viewMoreBtn.querySelector('.view-more-text');
      if (icon) {
        icon.className = 'bi me-1 view-more-icon ' + (expanded ? 'bi-chevron-up' : 'bi-chevron-down');
      }
      if (text) {
        text.textContent = expanded ? viewMoreBtn.dataset.textLess : viewMoreBtn.dataset.textMore;
      }
      viewMoreBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }

    if (viewMoreBtn && profileMoreInfo && typeof bootstrap !== 'undefined') {
      const moreCollapse = bootstrap.Collapse.getOrCreateInstance(profileMoreInfo, { toggle: false });

      if (viewMoreBtn._clickHandler) {
        viewMoreBtn.removeEventListener('click', viewMoreBtn._clickHandler);
      }
      viewMoreBtn._clickHandler = function () {
        const isExpanded = profileMoreInfo.classList.contains('show');
        if (isExpanded) {
          moreCollapse.hide();
          setViewMoreExpanded(false);
        } else {
          moreCollapse.show();
          setViewMoreExpanded(true);
        }
      };
      viewMoreBtn.addEventListener('click', viewMoreBtn._clickHandler);

      if (profileMoreInfo._shownHandler) {
        profileMoreInfo.removeEventListener('shown.bs.collapse', profileMoreInfo._shownHandler);
      }
      profileMoreInfo._shownHandler = function () { setViewMoreExpanded(true); };
      profileMoreInfo.addEventListener('shown.bs.collapse', profileMoreInfo._shownHandler);

      if (profileMoreInfo._hiddenHandler) {
        profileMoreInfo.removeEventListener('hidden.bs.collapse', profileMoreInfo._hiddenHandler);
      }
      profileMoreInfo._hiddenHandler = function () { setViewMoreExpanded(false); };
      profileMoreInfo.addEventListener('hidden.bs.collapse', profileMoreInfo._hiddenHandler);
    }

    // 4. Profile Completion Card Dismissal
    const completionCard = document.getElementById('profile-completion-card');
    const dismissCompletionBtn = document.getElementById('dismiss-completion-card');

    if (completionCard) {
      const completionDismissed = sessionStorage.getItem('profileCompletionDismissed');
      if (completionDismissed === 'true') {
        completionCard.style.display = 'none';
      }
    }

    if (dismissCompletionBtn && completionCard) {
      if (dismissCompletionBtn._clickHandler) {
        dismissCompletionBtn.removeEventListener('click', dismissCompletionBtn._clickHandler);
      }
      dismissCompletionBtn._clickHandler = function () {
        completionCard.style.display = 'none';
        sessionStorage.setItem('profileCompletionDismissed', 'true');
      };
      dismissCompletionBtn.addEventListener('click', dismissCompletionBtn._clickHandler);
    }
  }

  // 5. People Modal Event Handling (Delegated at document level once)
  let pendingConnectionType = null;
  let pendingConnectionTitle = null;
  let pendingProfileUsername = null;

  document.addEventListener('pointerdown', function (e) {
    const trigger = e.target.closest('.js-people-trigger');
    if (trigger) {
      pendingConnectionType = trigger.getAttribute('data-connection-type');
      pendingConnectionTitle = trigger.getAttribute('data-connection-title');
      pendingProfileUsername = trigger.getAttribute('data-profile-username');
    }
  }, true);

  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('.js-people-trigger');
    if (trigger) {
      pendingConnectionType = trigger.getAttribute('data-connection-type');
      pendingConnectionTitle = trigger.getAttribute('data-connection-title');
      pendingProfileUsername = trigger.getAttribute('data-profile-username');
    }
  }, true);

  document.addEventListener('show.bs.modal', function (event) {
    const modal = event.target;
    if (modal && modal.id === 'peopleModal') {
      const trigger = event.relatedTarget;
      let connectionType = pendingConnectionType;
      let title = pendingConnectionTitle || 'People';
      let profileUsername = pendingProfileUsername;

      if (trigger) {
        connectionType = connectionType || trigger.getAttribute('data-connection-type');
        title = trigger.getAttribute('data-connection-title') || title;
        profileUsername = trigger.getAttribute('data-profile-username') || profileUsername;
      }

      const modalTitle = document.getElementById('peopleModalTitle');
      const connTypeInput = document.getElementById('peopleConnectionType');
      const usernameInput = document.getElementById('peopleProfileUsername');
      const modalList = document.getElementById('peopleModalList');

      if (modalTitle) modalTitle.textContent = title;
      if (connTypeInput) connTypeInput.value = connectionType || '';
      if (usernameInput) usernameInput.value = profileUsername || '';

      if (modalList && connectionType && profileUsername && typeof htmx !== 'undefined') {
        const url = `/users/people/search/?connection_type=${encodeURIComponent(connectionType)}&profile_username=${encodeURIComponent(profileUsername)}`;
        htmx.ajax('GET', url, { target: '#peopleModalList', swap: 'innerHTML' });
      }
    }
  });

  document.addEventListener('hidden.bs.modal', function (event) {
    const modal = event.target;
    if (modal && modal.id === 'peopleModal') {
      const connTypeInput = document.getElementById('peopleConnectionType');
      const usernameInput = document.getElementById('peopleProfileUsername');
      const modalList = document.getElementById('peopleModalList');

      if (connTypeInput) connTypeInput.value = '';
      if (usernameInput) usernameInput.value = '';
      if (modalList) {
        modalList.innerHTML = '<div class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary" role="status"></div></div>';
      }
    }
  });

  // Attach lifecycle triggers
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProfilePage);
  } else {
    initProfilePage();
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    initProfilePage();
  });

  document.body.addEventListener('htmx:historyRestore', function (evt) {
    initProfilePage();
  });
})();
