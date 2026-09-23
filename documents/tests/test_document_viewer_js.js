/**
 * Unit test suite for DocumentViewer JavaScript architecture.
 * Runs in Node.js with a lightweight DOM mock to verify:
 * - Dual constructor compatibility
 * - Authoritative page state (paginated vs non-paginated)
 * - Page navigation boundaries
 * - Page change callbacks and state snapshots
 * - Single-instance fullscreen behavior
 * - Lifecycle cleanup
 */

const assert = require('assert');

// 1. Lightweight DOM mock
class MockElement {
    constructor(tagName = 'div') {
        this.tagName = tagName.toUpperCase();
        this._className = '';
        this.classList = {
            _classes: new Set(),
            add: (c) => {
                this.classList._classes.add(c);
                this._className = Array.from(this.classList._classes).join(' ');
            },
            remove: (c) => {
                this.classList._classes.delete(c);
                this._className = Array.from(this.classList._classes).join(' ');
            },
            contains: (c) => this.classList._classes.has(c),
        };
        this.style = {};
        this.dataset = {};
        this.children = [];
        this.parentElement = null;
        this.parentNode = null;
        this.id = '';
        this.attributes = {};
        this.listeners = {};
        this.disabled = false;
        this._innerHTML = '';
    }

    set className(val) {
        this._className = val || '';
        this.classList._classes.clear();
        if (val) {
            val.trim().split(/\s+/).forEach(c => this.classList._classes.add(c));
        }
    }

    get className() {
        return this._className;
    }

    set innerHTML(val) {
        this._innerHTML = val;
        this.children = [];
        if (!val) return;
        const matches = String(val).matchAll(/<([a-zA-Z0-9]+)([^>]*)>/g);
        for (const m of matches) {
            const tag = m[1];
            const attrs = m[2] || '';
            const child = new MockElement(tag);
            const classMatch = attrs.match(/class=["']([^"']+)["']/);
            if (classMatch) {
                classMatch[1].split(/\s+/).forEach(c => child.classList.add(c));
                child.className = classMatch[1];
            }
            const idMatch = attrs.match(/id=["']([^"']+)["']/);
            if (idMatch) {
                child.id = idMatch[1];
            }
            this.appendChild(child);
        }
    }

    get innerHTML() {
        return this._innerHTML;
    }

    appendChild(child) {
        if (child) {
            child.parentElement = this;
            child.parentNode = this;
            this.children.push(child);
        }
        return child;
    }

    insertBefore(newChild, refChild) {
        newChild.parentElement = this;
        newChild.parentNode = this;
        const idx = this.children.indexOf(refChild);
        if (idx >= 0) {
            this.children.splice(idx, 0, newChild);
        } else {
            this.children.push(newChild);
        }
        return newChild;
    }

    remove() {
        if (this.parentElement) {
            const idx = this.parentElement.children.indexOf(this);
            if (idx >= 0) this.parentElement.children.splice(idx, 1);
            this.parentElement = null;
            this.parentNode = null;
        }
    }

    querySelector(selector) {
        const find = (el) => {
            if (!el || !el.children) return null;
            for (const child of el.children) {
                if (selector.startsWith('.') && child.classList.contains(selector.slice(1))) return child;
                if (selector.startsWith('#') && child.id === selector.slice(1)) return child;
                if (selector.includes(' ') && selector.startsWith('.viewer-error') && selector.endsWith('button') && child.tagName === 'BUTTON') return child;
                if (selector.toLowerCase() === child.tagName.toLowerCase()) return child;
                const found = find(child);
                if (found) return found;
            }
            return null;
        };
        return find(this);
    }

    addEventListener(event, fn) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(fn);
    }

    removeEventListener(event, fn) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(f => f !== fn);
        }
    }

    setAttribute(key, val) {
        this.attributes[key] = val;
    }

    getAttribute(key) {
        return this.attributes[key];
    }
}

// Global browser mocks
global.document = {
    createElement: (tag) => new MockElement(tag),
    getElementById: (id) => null,
    querySelector: (sel) => null,
    addEventListener: (evt, fn) => {},
    removeEventListener: (evt, fn) => {},
    fullscreenElement: null,
    head: new MockElement('head'),
    body: new MockElement('body'),
};
global.window = {
    innerWidth: 1024,
    innerHeight: 768,
    devicePixelRatio: 1,
    addEventListener: () => {},
    removeEventListener: () => {},
};

// Mock ResizeObserver
global.ResizeObserver = class {
    constructor(cb) { this.cb = cb; }
    observe() {}
    unobserve() {}
    disconnect() {}
};

// Require DocumentViewer module
const { DocumentViewer, ViewerFactory, UnsupportedViewer } = require('../static/documents/js/document-viewer.js');

// Mock PDF Viewer for ViewerFactory
class MockPaginatedViewer {
    constructor(container, fileUrl, options) {
        this.container = container;
        this.totalPages = 12;
        this.currentPage = options.initialPage || 1;
    }
    async load() {}
    getTotalPages() { return this.totalPages; }
    needsToolbar() { return true; }
    needsPageNavigation() { return true; }
    needsZoom() { return true; }
    needsScroll() { return false; }
    async goToPage(p) { this.currentPage = p; }
    async zoomIn() {}
    async zoomOut() {}
    handleResize() {}
    destroy() {}
}

class MockNonPaginatedViewer {
    constructor(container, fileUrl, options) {
        this.container = container;
    }
    async load() {}
    getTotalPages() { return null; }
    needsToolbar() { return true; }
    needsPageNavigation() { return false; }
    needsZoom() { return true; }
    needsScroll() { return true; }
    scrollUp() {}
    scrollDown() {}
    async zoomIn() {}
    async zoomOut() {}
    handleResize() {}
    destroy() {}
}

// Override ViewerFactory createViewer for unit tests
const originalCreateViewer = ViewerFactory.createViewer;

async function runTests() {
    let passed = 0;
    let failed = 0;

    function test(name, fn) {
        try {
            fn();
            console.log(`  ✓ ${name}`);
            passed++;
        } catch (err) {
            console.error(`  ✗ ${name}:`, err.message);
            failed++;
        }
    }

    async function asyncTest(name, fn) {
        try {
            await fn();
            console.log(`  ✓ ${name}`);
            passed++;
        } catch (err) {
            console.error(`  ✗ ${name}:`, err.message);
            failed++;
        }
    }

    console.log('Running DocumentViewer JavaScript Unit Tests...\n');

    // Test 1: Modern Options Constructor
    test('Constructor accepts modern options object signature', () => {
        const container = new MockElement('div');
        const options = {
            documentId: 'doc-uuid-123',
            documentVersionId: 42,
            fileId: 101,
            fileUrl: '/media/test.pdf',
            fileType: 'pdf',
            fileName: 'TestDoc.pdf',
            initialPage: 3,
            fitContainer: true,
            compact: true
        };
        const viewer = new DocumentViewer(container, options);

        assert.strictEqual(viewer.documentId, 'doc-uuid-123');
        assert.strictEqual(viewer.documentVersionId, 42);
        assert.strictEqual(viewer.fileId, 101);
        assert.strictEqual(viewer.fileUrl, '/media/test.pdf');
        assert.strictEqual(viewer.fileType, 'pdf');
        assert.strictEqual(viewer.fileName, 'TestDoc.pdf');
        assert.strictEqual(viewer.currentPage, 3);
        assert.strictEqual(viewer.options.fitContainer, true);
        assert.strictEqual(viewer.options.compact, true);
    });

    // Test 2: Legacy Positional Constructor
    test('Constructor preserves backward-compatible positional signature', () => {
        const container = new MockElement('div');
        const legacyOptions = { documentVersionId: 77, compact: false };
        const viewer = new DocumentViewer(
            container,
            '/media/legacy.pdf',
            'PDF',
            'Legacy.pdf',
            'doc-legacy-uuid',
            202,
            legacyOptions
        );

        assert.strictEqual(viewer.documentId, 'doc-legacy-uuid');
        assert.strictEqual(viewer.documentVersionId, 77);
        assert.strictEqual(viewer.fileId, 202);
        assert.strictEqual(viewer.fileUrl, '/media/legacy.pdf');
        assert.strictEqual(viewer.fileType, 'pdf');
        assert.strictEqual(viewer.fileName, 'Legacy.pdf');
    });

    // Test 3: Paginated Format Lifecycle & State Contract
    await asyncTest('Paginated document (PDF) exposes non-null currentPage and totalPages', async () => {
        ViewerFactory.createViewer = (ft, c, url, opts) => new MockPaginatedViewer(c, url, opts);

        const container = new MockElement('div');
        let reportedPage = null;
        let reportedTotal = null;
        let reportedState = null;

        const viewer = new DocumentViewer(container, {
            documentId: 'pdf-doc',
            documentVersionId: 1,
            fileType: 'pdf',
            fileUrl: '/test.pdf',
            initialPage: 2,
            onPageChange: (page, total, state) => {
                reportedPage = page;
                reportedTotal = total;
                reportedState = state;
            }
        });

        await viewer.initialize();

        assert.strictEqual(viewer.isPaginated, true);
        assert.strictEqual(viewer.getCurrentPage(), 2);
        assert.strictEqual(viewer.getTotalPages(), 12);
        assert.strictEqual(reportedPage, 2);
        assert.strictEqual(reportedTotal, 12);
        assert.ok(reportedState);
        assert.strictEqual(reportedState.currentPage, 2);
        assert.strictEqual(reportedState.totalPages, 12);
        assert.strictEqual(reportedState.isPaginated, true);
        assert.strictEqual(reportedState.documentId, 'pdf-doc');
        assert.strictEqual(reportedState.documentVersionId, 1);
    });

    // Test 4: Non-Paginated Format State Contract
    await asyncTest('Non-paginated document (DOCX) sets currentPage and totalPages to null', async () => {
        ViewerFactory.createViewer = (ft, c, url, opts) => new MockNonPaginatedViewer(c, url, opts);

        const container = new MockElement('div');
        let reportedPage = -1;
        let reportedTotal = -1;

        const viewer = new DocumentViewer(container, {
            documentId: 'docx-doc',
            fileType: 'docx',
            fileUrl: '/test.docx',
            onPageChange: (page, total) => {
                reportedPage = page;
                reportedTotal = total;
            }
        });

        await viewer.initialize();

        assert.strictEqual(viewer.isPaginated, false);
        assert.strictEqual(viewer.getCurrentPage(), null);
        assert.strictEqual(viewer.getTotalPages(), null);
        assert.strictEqual(reportedPage, null);
        assert.strictEqual(reportedTotal, null);

        const state = viewer.getState();
        assert.strictEqual(state.currentPage, null);
        assert.strictEqual(state.totalPages, null);
        assert.strictEqual(state.isPaginated, false);
    });

    // Test 5: Page Navigation & Boundary Invariants
    await asyncTest('goToPage enforces strict boundary invariants [1, totalPages]', async () => {
        ViewerFactory.createViewer = (ft, c, url, opts) => new MockPaginatedViewer(c, url, opts);

        const container = new MockElement('div');
        const pageHistory = [];

        const viewer = new DocumentViewer(container, {
            documentId: 'boundary-doc',
            fileType: 'pdf',
            fileUrl: '/boundary.pdf',
            initialPage: 1,
            onPageChange: (page) => pageHistory.push(page)
        });

        await viewer.initialize();
        assert.strictEqual(viewer.getCurrentPage(), 1);

        // Next page
        await viewer.nextPage();
        assert.strictEqual(viewer.getCurrentPage(), 2);

        // Direct navigation
        await viewer.goToPage(10);
        assert.strictEqual(viewer.getCurrentPage(), 10);

        // Attempt invalid bounds: 0, negative, > totalPages, non-number
        await viewer.goToPage(0);
        assert.strictEqual(viewer.getCurrentPage(), 10); // unchanged

        await viewer.goToPage(-3);
        assert.strictEqual(viewer.getCurrentPage(), 10); // unchanged

        await viewer.goToPage(13); // total is 12
        assert.strictEqual(viewer.getCurrentPage(), 10); // unchanged

        await viewer.goToPage('invalid');
        assert.strictEqual(viewer.getCurrentPage(), 10); // unchanged

        // Reaching boundaries
        await viewer.goToPage(12);
        assert.strictEqual(viewer.getCurrentPage(), 12);
        await viewer.nextPage();
        assert.strictEqual(viewer.getCurrentPage(), 12); // cannot exceed totalPages

        await viewer.goToPage(1);
        assert.strictEqual(viewer.getCurrentPage(), 1);
        await viewer.previousPage();
        assert.strictEqual(viewer.getCurrentPage(), 1); // cannot go below 1
    });

    // Test 6: Single-Instance Fullscreen Mode
    await asyncTest('Fullscreen preserves single viewer state and current page', async () => {
        ViewerFactory.createViewer = (ft, c, url, opts) => new MockPaginatedViewer(c, url, opts);

        const container = new MockElement('div');
        const viewer = new DocumentViewer(container, {
            documentId: 'fs-doc',
            fileType: 'pdf',
            fileUrl: '/fs.pdf',
            initialPage: 7
        });

        await viewer.initialize();
        assert.strictEqual(viewer.getCurrentPage(), 7);
        assert.strictEqual(viewer.isFullscreen, false);

        // Enter fullscreen
        viewer.enterFullscreen();
        assert.strictEqual(viewer.isFullscreen, true);
        assert.strictEqual(viewer.getCurrentPage(), 7);
        assert.ok(container.classList.contains('viewer-fullscreen'));

        // Navigate while in fullscreen
        await viewer.nextPage();
        assert.strictEqual(viewer.getCurrentPage(), 8);

        // Exit fullscreen
        viewer.exitFullscreen(false);
        assert.strictEqual(viewer.isFullscreen, false);
        assert.strictEqual(viewer.getCurrentPage(), 8); // Preserved!
        assert.strictEqual(container.classList.contains('viewer-fullscreen'), false);
    });

    // Test 7: Clean Lifecycle & Teardown
    await asyncTest('destroy() unmounts cleanly and cleans up observer and listeners', async () => {
        let destroyed = false;
        ViewerFactory.createViewer = (ft, c, url, opts) => ({
            load: async () => {},
            getTotalPages: () => 5,
            needsToolbar: () => true,
            needsPageNavigation: () => true,
            needsZoom: () => false,
            needsScroll: () => false,
            destroy: () => { destroyed = true; }
        });

        const container = new MockElement('div');
        container._documentViewer = null;

        const viewer = new DocumentViewer(container, {
            documentId: 'destroy-doc',
            fileType: 'pdf',
            fileUrl: '/d.pdf'
        });
        container._documentViewer = viewer;

        await viewer.initialize();
        assert.ok(viewer.toolbar);

        // Destroy
        viewer.destroy();
        assert.strictEqual(destroyed, true);
        assert.strictEqual(viewer.toolbar, null);
        assert.strictEqual(viewer.viewer, null);
        assert.strictEqual(viewer.resizeObserver, null);
        assert.strictEqual(container._documentViewer, undefined);
    });

    // Test 8: File Type Normalization in ViewerFactory & DocumentViewer
    test('ViewerFactory normalizes leading dots and derives extension from url/filename', () => {
        assert.strictEqual(ViewerFactory.normalizeFileType('.pdf'), 'pdf');
        assert.strictEqual(ViewerFactory.normalizeFileType('.DOCX'), 'docx');
        assert.strictEqual(ViewerFactory.normalizeFileType('', 'https://example.com/lecture.pdf?token=123'), 'pdf');
        assert.strictEqual(ViewerFactory.normalizeFileType(null, null, { fileName: 'Homework.pptx' }), 'pptx');

        const container = new MockElement('div');
        const v1 = new DocumentViewer(container, { fileType: '.PDF', fileUrl: '/test.pdf' });
        assert.strictEqual(v1.fileType, 'pdf');

        const v2 = new DocumentViewer(container, { fileType: '', fileUrl: '/media/files/doc.pdf?v=1' });
        assert.strictEqual(v2.fileType, 'pdf');
    });

    // Test 9: Modern Top Toolbar & Bottom Floating Pill Bar Controls
    await asyncTest('creates sleek top header toolbar and bottom floating pill bar controls', async () => {
        ViewerFactory.createViewer = (ft, c, url, opts) => new MockPaginatedViewer(c, url, opts);

        const container = new MockElement('div');
        const viewer = new DocumentViewer(container, {
            documentId: 'toolbar-doc',
            fileType: 'pdf',
            fileName: 'Quantum_Mechanics_Lecture_01.pdf',
            fileUrl: '/qm.pdf',
            initialPage: 4
        });

        await viewer.initialize();
        assert.ok(viewer.toolbar, 'Top toolbar element should be created');
        assert.ok(viewer.floatingBar, 'Bottom floating bar element should be created');

        // Top Toolbar Left: Format badge & Title
        const badge = viewer.toolbar.querySelector('.viewer-doc-type-indicator');
        assert.ok(badge, 'Document format badge must exist in top toolbar');
        assert.strictEqual(badge.textContent, 'PDF');

        const title = viewer.toolbar.querySelector('.viewer-doc-title');
        assert.ok(title, 'Document title element must exist on desktop');
        assert.strictEqual(title.textContent, 'Quantum_Mechanics_Lecture_01.pdf');

        // Top Toolbar Right: Reload button, Fullscreen button, Download button
        const reloadBtn = viewer.toolbar.querySelector('.viewer-reload-btn');
        assert.ok(reloadBtn, 'Reload button must exist in top toolbar');

        const fullscreenBtn = viewer.toolbar.querySelector('.viewer-fullscreen-btn');
        assert.ok(fullscreenBtn, 'Fullscreen button must exist in top toolbar');

        const downloadBtn = viewer.toolbar.querySelector('.viewer-download-btn');
        assert.ok(downloadBtn, 'Download button must exist in top toolbar');

        // Bottom Floating Bar: Page navigation pill & Zoom pill
        const pagePill = viewer.floatingBar.querySelector('.viewer-page-nav-pill');
        assert.ok(pagePill, 'Page navigation pill must exist in bottom floating bar');
        const prevBtn = pagePill.querySelector('.viewer-prev-btn');
        const nextBtn = pagePill.querySelector('.viewer-next-btn');
        const currentPg = pagePill.querySelector('.viewer-current-page');
        const totalPgs = pagePill.querySelector('.viewer-total-pages');
        assert.ok(prevBtn, 'Previous button must exist in page pill');
        assert.ok(nextBtn, 'Next button must exist in page pill');
        assert.strictEqual(String(currentPg.textContent), '4');
        assert.strictEqual(String(totalPgs.textContent), '12');

        const zoomPill = viewer.floatingBar.querySelector('.viewer-zoom-pill');
        assert.ok(zoomPill, 'Zoom pill must exist in bottom floating bar');
        const zoomIndicator = zoomPill.querySelector('.viewer-zoom-indicator');
        assert.ok(zoomIndicator, 'Zoom indicator must exist in zoom pill');
    });

    // Test 10: Interactive Retry Button in showError() and UnsupportedViewer
    await asyncTest('showError and UnsupportedViewer provide working Reload Document action', async () => {
        const container = new MockElement('div');
        let reloaded = false;
        global.window.reloadDocumentDetailViewer = () => { reloaded = true; };

        const viewer = new DocumentViewer(container, {
            documentId: 'retry-doc',
            fileType: 'pdf',
            fileUrl: '/retry.pdf'
        });

        // 1. Test showError
        viewer.showError('Simulated network error');
        const retryBtn = container.querySelector('#viewer-retry-btn');
        assert.ok(retryBtn, 'Reload Document button must exist in error state');
        assert.strictEqual(typeof retryBtn.onclick, 'function');
        retryBtn.onclick();
        assert.strictEqual(reloaded, true, 'Clicking retry must call window.reloadDocumentDetailViewer()');

        // 2. Test UnsupportedViewer
        reloaded = false;
        const unsupp = new UnsupportedViewer(container, '/media/unknown.xyz', 'xyz');
        await unsupp.load();
        const unsuppRetryBtn = container.querySelector('#viewer-retry-btn');
        assert.ok(unsuppRetryBtn, 'Reload Document button must exist in UnsupportedViewer');
        unsuppRetryBtn.onclick();
        assert.strictEqual(reloaded, true, 'Clicking retry in UnsupportedViewer must call window.reloadDocumentDetailViewer()');

        delete global.window.reloadDocumentDetailViewer;
    });

    // Restore original factory
    ViewerFactory.createViewer = originalCreateViewer;

    console.log(`\nTests finished: ${passed} passed, ${failed} failed.`);
    if (failed > 0) {
        process.exit(1);
    }
}

runTests();
