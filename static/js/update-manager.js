/**
 * PwaniNet Update Manager
 * Update detection and notification system
 * Release Center is the single source of truth for version information.
 */

(function() {
    'use strict';

    // State
    let currentVersion = null;
    let currentBuild = null;
    let latestVersion = null;
    let latestBuild = null;
    let serviceWorkerRegistration = null;
    let updateAvailable = false;

    // Check for updates on page load
    async function checkForUpdates() {
        try {
            // Fetch current version from Release Center (single source of truth)
            const response = await fetch('/api/version/');
            const data = await response.json();

            currentVersion = data.version;
            currentBuild = data.build;

            // Fetch latest published release
            const latestResponse = await fetch('/api/releases/version_check/');
            const latestData = await latestResponse.json();

            latestVersion = latestData.latest_version;
            latestBuild = latestData.latest_build_number;

            // Compare versions
            if (latestData.update_available) {
                console.log('[UpdateManager] New version available:', latestVersion, 'build', latestBuild);
                updateAvailable = true;
                showUpdateModal(latestData);
            } else {
                console.log('[UpdateManager] Application is up to date');
                updateAvailable = false;
            }
        } catch (error) {
            console.warn('[UpdateManager] Failed to check for updates:', error);
        }
    }

    // Show custom update modal with release details
    function showUpdateModal(releaseData) {
        // Check if modal already exists
        if (document.getElementById('update-modal')) {
            return;
        }

        // Check if update was previously dismissed
        const dismissed = localStorage.getItem('update-dismissed');
        if (dismissed === `${releaseData.latest_version}-${releaseData.latest_build_number}`) {
            return;
        }

        // Check if user is on mandatory update
        if (releaseData.mandatory_update) {
            showMandatoryUpdateModal(releaseData);
            return;
        }

        // Create modal
        const modal = document.createElement('div');
        modal.id = 'update-modal';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">PwaniNet Update Available</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <h4 class="fw-bold">Version ${releaseData.latest_version}</h4>
                            <p class="text-muted mb-0">Build ${releaseData.latest_build_number}</p>
                            <p class="text-muted small">${releaseData.release_channel || 'Stable'}</p>
                        </div>
                        
                        <h6 class="fw-bold mb-2">${releaseData.release_title || 'Update Available'}</h6>
                        <p class="text-muted mb-3">${releaseData.release_summary || 'A new version is available for download.'}</p>
                        
                        ${releaseData.release_notes && releaseData.release_notes.length > 0 ? `
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="fw-bold mb-2">What's New</h6>
                                <ul class="list-unstyled mb-0">
                                    ${releaseData.release_notes.map(note => `
                                        <li class="mb-1">
                                            <small><strong>${note.category}:</strong> ${note.title}</small>
                                            ${note.description ? `<br><small class="text-muted">${note.description}</small>` : ''}
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="update-later-btn">Later</button>
                        <button type="button" class="btn btn-primary" id="update-now-btn">Update Now</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Initialize Bootstrap modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Add event listeners
        document.getElementById('update-later-btn').addEventListener('click', function() {
            bootstrapModal.hide();
            modal.remove();
            // Store dismissal in localStorage
            localStorage.setItem('update-dismissed', `${releaseData.latest_version}-${releaseData.latest_build_number}`);
        });

        document.getElementById('update-now-btn').addEventListener('click', function() {
            bootstrapModal.hide();
            modal.remove();
            initiateUpdate(releaseData);
        });

        // Clean up on modal hide
        modal.addEventListener('hidden.bs.modal', function() {
            modal.remove();
        });
    }

    // Show mandatory update modal (no "Later" option)
    function showMandatoryUpdateModal(releaseData) {
        const modal = document.createElement('div');
        modal.id = 'update-modal';
        modal.className = 'modal fade';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning">
                        <h5 class="modal-title">⚠️ Mandatory Update Required</h5>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <h4 class="fw-bold">Version ${releaseData.latest_version}</h4>
                            <p class="text-muted mb-0">Build ${releaseData.latest_build_number}</p>
                        </div>
                        
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle-fill me-2"></i>
                            This is a mandatory update. You must update to continue using PwaniNet.
                        </div>
                        
                        <h6 class="fw-bold mb-2">${releaseData.release_title || 'Mandatory Update'}</h6>
                        <p class="text-muted mb-3">${releaseData.release_summary || 'A mandatory update is required.'}</p>
                        
                        ${releaseData.release_notes && releaseData.release_notes.length > 0 ? `
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="fw-bold mb-2">What's New</h6>
                                <ul class="list-unstyled mb-0">
                                    ${releaseData.release_notes.map(note => `
                                        <li class="mb-1">
                                            <small><strong>${note.category}:</strong> ${note.title}</small>
                                            ${note.description ? `<br><small class="text-muted">${note.description}</small>` : ''}
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary w-100" id="mandatory-update-btn">Update Now</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Initialize Bootstrap modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Add event listener
        document.getElementById('mandatory-update-btn').addEventListener('click', function() {
            bootstrapModal.hide();
            modal.remove();
            initiateUpdate(releaseData);
        });
    }

    // Initiate update process
    async function initiateUpdate(releaseData) {
        showProgressModal();

        try {
            // Check for waiting service worker
            if (serviceWorkerRegistration && serviceWorkerRegistration.waiting) {
                // Service worker is already waiting, just activate it
                await activateServiceWorker();
            } else {
                // Trigger service worker update check
                if (serviceWorkerRegistration) {
                    await serviceWorkerRegistration.update();
                    // Wait a bit for the new worker to install
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    if (serviceWorkerRegistration.waiting) {
                        await activateServiceWorker();
                    } else {
                        // No waiting worker, just reload
                        console.log('[UpdateManager] No waiting service worker, reloading page');
                        updateProgress('Reloading...', 100);
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        window.location.reload();
                    }
                } else {
                    // No service worker registration, just reload
                    console.log('[UpdateManager] No service worker registration, reloading page');
                    updateProgress('Reloading...', 100);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    window.location.reload();
                }
            }
        } catch (error) {
            console.error('[UpdateManager] Update failed:', error);
            hideProgressModal();
            alert('Update failed. Please refresh the page manually.');
        }
    }

    // Activate waiting service worker
    async function activateServiceWorker() {
        updateProgress('Activating update...', 80);
        
        return new Promise((resolve) => {
            const waitingWorker = serviceWorkerRegistration.waiting;
            
            // Send skipWaiting message
            waitingWorker.postMessage({ type: 'SKIP_WAITING' });
            
            // Listen for controller change
            navigator.serviceWorker.addEventListener('controllerchange', function handler() {
                navigator.serviceWorker.removeEventListener('controllerchange', handler);
                updateProgress('Restarting...', 100);
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            });
        });
    }

    // Show progress modal
    function showProgressModal() {
        if (document.getElementById('update-progress-modal')) {
            return;
        }

        const modal = document.createElement('div');
        modal.id = 'update-progress-modal';
        modal.className = 'modal fade';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h5 class="fw-bold mb-2">Updating PwaniNet</h5>
                        <p class="text-muted mb-3" id="progress-text">Preparing update...</p>
                        <div class="progress" style="height: 6px;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 id="progress-bar" 
                                 role="progressbar" 
                                 style="width: 0%"></div>
                        </div>
                        <p class="text-muted small mt-2">Please don't close the application.</p>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }

    // Update progress
    function updateProgress(text, percentage) {
        const progressText = document.getElementById('progress-text');
        const progressBar = document.getElementById('progress-bar');
        
        if (progressText) {
            progressText.textContent = text;
        }
        if (progressBar) {
            progressBar.style.width = percentage + '%';
        }
    }

    // Hide progress modal
    function hideProgressModal() {
        const modal = document.getElementById('update-progress-modal');
        if (modal) {
            const bootstrapModal = bootstrap.Modal.getInstance(modal);
            if (bootstrapModal) {
                bootstrapModal.hide();
            }
            modal.remove();
        }
    }

    // Initialize service worker registration
    async function initServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.log('[UpdateManager] Service Worker not supported');
            return;
        }

        try {
            // Fetch current version info first
            const versionResponse = await fetch('/api/version/');
            const versionData = await versionResponse.json();

            serviceWorkerRegistration = await navigator.serviceWorker.register('/service-worker.js');
            console.log('[UpdateManager] Service Worker registered');

            // Send version info to service worker for cache naming
            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage({
                    type: 'SET_VERSION',
                    version: versionData.version,
                    build: versionData.build,
                    environment: versionData.environment,
                    buildDate: versionData.release_date
                });
            }

            // Listen for service worker updates
            serviceWorkerRegistration.addEventListener('updatefound', () => {
                const newWorker = serviceWorkerRegistration.installing;
                console.log('[UpdateManager] New service worker found');
                
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        console.log('[UpdateManager] New service worker installed and waiting');
                        // Don't activate automatically - wait for user approval
                    }
                });
            });
        } catch (error) {
            console.error('[UpdateManager] Service Worker registration failed:', error);
        }
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initServiceWorker();
            // Delay check slightly to not interfere with initial page load
            setTimeout(checkForUpdates, 2000);
        });
    } else {
        initServiceWorker();
        setTimeout(checkForUpdates, 2000);
    }

    // Periodic check every 5 minutes
    setInterval(checkForUpdates, 300000);

    // Expose API for manual checks
    window.PwaniNetUpdateManager = {
        checkForUpdates,
        initiateUpdate,
        isUpdateAvailable: () => updateAvailable
    };

})();
