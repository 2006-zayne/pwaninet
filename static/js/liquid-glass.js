(() => {
  const html = document.documentElement;
  const nav = document.querySelector('.navbar-top, .lg-topbar');
  const tabBar = document.querySelector('.mobile-bottom-nav');
  const pressables = document.querySelectorAll('button, .btn, .nav-chip, .dropdown-item, a');

  const supportsBackdrop = (() => {
    const value = CSS.supports('backdrop-filter: blur(1px)') || CSS.supports('-webkit-backdrop-filter: blur(1px)');
    return Boolean(value);
  })();

  if (!supportsBackdrop) {
    html.classList.add('lg-nofilter');
  }

  if (nav) {
    const updateNavState = () => {
      const scrolled = window.scrollY > 8;
      nav.classList.toggle('lg-nav--scrolled', scrolled);
    };

    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          updateNavState();
          ticking = false;
        });
        ticking = true;
      }
    };

    updateNavState();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  if (tabBar) {
    let lastY = window.scrollY;
    let ticking = false;

    const updateTabBar = () => {
      const currentY = window.scrollY;
      const delta = currentY - lastY;
      if (Math.abs(delta) > 4) {
        tabBar.classList.toggle('lg-tabbar--hidden', delta > 0 && currentY > 120);
        lastY = currentY;
      }
    };

    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          updateTabBar();
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
  }

  pressables.forEach((element) => {
    const activate = (event) => {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      element.classList.add('lg-press');
    };

    const deactivate = () => element.classList.remove('lg-press');

    element.addEventListener('pointerdown', activate);
    element.addEventListener('pointerup', deactivate);
    element.addEventListener('pointerleave', deactivate);
    element.addEventListener('pointercancel', deactivate);
  });
})();
