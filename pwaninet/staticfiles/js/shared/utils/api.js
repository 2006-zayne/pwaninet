/**
 * API Client Utility
 * Centralized API request handling with CSRF token injection
 */

import { getCSRFToken } from './csrf.js';

/**
 * Make an API request with automatic CSRF token injection
 * @param {string} url - API endpoint URL
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function apiRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    credentials: 'same-origin'
  };

  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers
    }
  };

  return fetch(url, mergedOptions);
}

/**
 * Make a GET request
 * @param {string} url - API endpoint URL
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function get(url, options = {}) {
  return apiRequest(url, { ...options, method: 'GET' });
}

/**
 * Make a POST request
 * @param {string} url - API endpoint URL
 * @param {object} data - Request body data
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function post(url, data, options = {}) {
  return apiRequest(url, {
    ...options,
    method: 'POST',
    body: JSON.stringify(data)
  });
}

/**
 * Make a PUT request
 * @param {string} url - API endpoint URL
 * @param {object} data - Request body data
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function put(url, data, options = {}) {
  return apiRequest(url, {
    ...options,
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

/**
 * Make a PATCH request
 * @param {string} url - API endpoint URL
 * @param {object} data - Request body data
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function patch(url, data, options = {}) {
  return apiRequest(url, {
    ...options,
    method: 'PATCH',
    body: JSON.stringify(data)
  });
}

/**
 * Make a DELETE request
 * @param {string} url - API endpoint URL
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function del(url, options = {}) {
  return apiRequest(url, { ...options, method: 'DELETE' });
}

/**
 * Handle API response with error checking
 * @param {Response} response - Fetch response
 * @returns {Promise<object>} Parsed JSON response
 * @throws {Error} If response is not ok
 */
export async function handleResponse(response) {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  return response.json();
}
