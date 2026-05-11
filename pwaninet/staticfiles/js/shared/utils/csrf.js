/**
 * CSRF Token Utility
 * Centralized CSRF token retrieval from multiple sources
 */

/**
 * Get CSRF token from various sources in priority order
 * @returns {string} CSRF token or empty string if not found
 */
export function getCSRFToken() {
  // Priority 1: Hidden input field
  const tokenFromInput = document.querySelector('[name="csrfmiddlewaretoken"]');
  if (tokenFromInput) return tokenFromInput.value;

  // Priority 2: Meta tag
  const tokenFromMeta = document.querySelector('meta[name="csrf-token"]');
  if (tokenFromMeta) return tokenFromMeta.content;

  // Priority 3: Cookie
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  if (cookieValue) return cookieValue;

  return '';
}

/**
 * Set CSRF token in all possible locations
 * @param {string} token - CSRF token to set
 */
export function setCSRFToken(token) {
  // Set in hidden input
  const input = document.querySelector('[name="csrfmiddlewaretoken"]');
  if (input) input.value = token;

  // Set in meta tag
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) meta.content = token;

  // Set in cookie (7 days expiry)
  document.cookie = `csrftoken=${token}; path=/; max-age=604800; SameSite=Lax`;
}
