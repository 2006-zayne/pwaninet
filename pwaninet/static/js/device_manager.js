/**
 * Device Manager - Handles device identification for account switching
 * Stores device ID in localStorage and sends it with all HTMX requests
 */

const DEVICE_ID_KEY = 'pwaninet_device_id';

/**
 * Generate a random device ID
 */
function generateDeviceId() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or create device ID from localStorage
 */
function getOrCreateDeviceId() {
    let deviceId = localStorage.getItem(DEVICE_ID_KEY);
    
    if (!deviceId) {
        deviceId = generateDeviceId();
        localStorage.setItem(DEVICE_ID_KEY, deviceId);
    }
    
    return deviceId;
}

/**
 * Initialize device manager
 * Sets up HTMX to include device ID in all requests
 */
function initDeviceManager() {
    const deviceId = getOrCreateDeviceId();

    // Configure HTMX to include device ID in all requests
    if (typeof htmx !== 'undefined') {
        htmx.defineExtension('device-id', {
            onEvent: function(name, evt) {
                if (name === 'htmx:beforeRequest') {
                    evt.detail.xhr.setRequestHeader('X-Device-ID', deviceId);
                }
            }
        });

        // Add the extension to the body so it applies to all HTMX requests
        document.body.setAttribute('hx-ext', 'device-id');
    }

    console.log('Device Manager initialized with ID:', deviceId.substring(0, 8) + '...');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDeviceManager);
} else {
    initDeviceManager();
}
