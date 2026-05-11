/**
 * Notification Utility
 * Centralized notification display system
 */

/**
 * Show a notification to the user
 * @param {string} message - Notification message
 * @param {string} type - Notification type (info, success, warning, danger, primary)
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
export function showNotification(message, type = 'info', duration = 3000) {
  const notification = document.createElement('div');
  const alertType = type === 'info' ? 'primary' : type;
  
  notification.className = `alert alert-${alertType} alert-dismissible fade show position-fixed`;
  notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
  notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  
  document.body.appendChild(notification);
  
  // Auto-remove after duration
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 150); // Wait for fade out
  }, duration);
}

/**
 * Show a success notification
 * @param {string} message - Success message
 * @param {number} duration - Duration in milliseconds
 */
export function showSuccess(message, duration = 3000) {
  showNotification(message, 'success', duration);
}

/**
 * Show an error notification
 * @param {string} message - Error message
 * @param {number} duration - Duration in milliseconds
 */
export function showError(message, duration = 5000) {
  showNotification(message, 'danger', duration);
}

/**
 * Show a warning notification
 * @param {string} message - Warning message
 * @param {number} duration - Duration in milliseconds
 */
export function showWarning(message, duration = 4000) {
  showNotification(message, 'warning', duration);
}

/**
 * Show an info notification
 * @param {string} message - Info message
 * @param {number} duration - Duration in milliseconds
 */
export function showInfo(message, duration = 3000) {
  showNotification(message, 'info', duration);
}
