/* Paste into DevTools Console on a logged-in staging page before navigating. */
(() => {
  if (window.PwaniNetPerfProbe) {
    console.info('PwaniNet performance probe is already running.');
    return;
  }

  const records = [];
  const active = new Map();
  const longTasks = [];
  let nextId = 1;
  const now = () => performance.now();
  const route = (url) => {
    try { return new URL(url, location.href).pathname; } catch (_) { return String(url || ''); }
  };
  const isPageTarget = (event) => event.detail?.target?.id === 'page-content-target';

  document.addEventListener('htmx:beforeRequest', (event) => {
    if (!isPageTarget(event)) return;
    const id = nextId++;
    active.set(event.detail.xhr, {
      id,
      path: route(event.detail.requestConfig?.path || event.detail.elt?.getAttribute('hx-get') || location.href),
      started: now(),
      userStart: performance.timeOrigin + now(),
    });
  });

  document.addEventListener('htmx:afterRequest', (event) => {
    if (!isPageTarget(event)) return;
    const item = active.get(event.detail.xhr);
    if (!item) return;
    item.responseAt = now();
    item.status = event.detail.xhr.status;
  });

  document.addEventListener('htmx:afterSwap', (event) => {
    if (!isPageTarget(event)) return;
    const item = active.get(event.detail.xhr);
    if (!item) return;
    item.swapAt = now();
  });

  document.addEventListener('htmx:afterSettle', (event) => {
    if (!isPageTarget(event)) return;
    const item = active.get(event.detail.xhr);
    if (!item) return;
    item.settleAt = now();
    requestAnimationFrame(() => requestAnimationFrame(() => {
      item.paintedAt = now();
      item.totalMs = +(item.paintedAt - item.started).toFixed(1);
      item.serverTiming = event.detail.xhr.getResponseHeader('Server-Timing') || '';
      item.requestId = event.detail.xhr.getResponseHeader('X-Request-ID') || '';
      item.responseBytes = event.detail.xhr.responseText?.length || 0;
      records.push(item);
      active.delete(event.detail.xhr);
      console.info('[PwaniNet perf]', item);
    }));
  });

  for (const eventName of ['htmx:responseError', 'htmx:sendError', 'htmx:sendAbort']) {
    document.addEventListener(eventName, (event) => {
      if (!isPageTarget(event)) return;
      const item = active.get(event.detail?.xhr);
      if (item) {
        item.error = eventName;
        item.finishedAt = now();
        records.push(item);
        active.delete(event.detail.xhr);
        console.warn('[PwaniNet perf]', item);
      }
    });
  }

  if ('PerformanceObserver' in window) {
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          longTasks.push({ startTime: +entry.startTime.toFixed(1), durationMs: +entry.duration.toFixed(1) });
        }
      }).observe({ type: 'longtask', buffered: true });
    } catch (_) {}
  }

  window.PwaniNetPerfProbe = {
    getReport() {
      return {
        capturedAt: new Date().toISOString(),
        userAgent: navigator.userAgent,
        navigations: [...records],
        longTasks: [...longTasks],
        resources: performance.getEntriesByType('resource').map((entry) => {
          let safeName = entry.name;
          try {
            const url = new URL(entry.name, location.href);
            safeName = `${url.origin}${url.pathname}`;
          } catch (_) {}
          return {
            name: safeName,
            initiator: entry.initiatorType,
            durationMs: +entry.duration.toFixed(1),
            transferBytes: entry.transferSize || 0,
            encodedBytes: entry.encodedBodySize || 0,
            decodedBytes: entry.decodedBodySize || 0,
          };
        }),
        pageLoad: performance.getEntriesByType('navigation').map((entry) => ({
          dnsMs: +(entry.domainLookupEnd - entry.domainLookupStart).toFixed(1),
          connectMs: +(entry.connectEnd - entry.connectStart).toFixed(1),
          ttfbMs: +entry.responseStart.toFixed(1),
          domContentLoadedMs: +entry.domContentLoadedEventEnd.toFixed(1),
          loadMs: +entry.loadEventEnd.toFixed(1),
        })),
      };
    },
    download() {
      const blob = new Blob([JSON.stringify(this.getReport(), null, 2)], { type: 'application/json' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'pwaninet-browser-performance.json';
      link.click();
      URL.revokeObjectURL(link.href);
    },
  };

  console.info('PwaniNet perf probe ready. Navigate through Home, Profile, and Groups, then run PwaniNetPerfProbe.download().');
})();
