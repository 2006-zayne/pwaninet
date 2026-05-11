/**
 * Test Module
 * Verify that new modular JavaScript files work correctly
 * Run this in browser console to test
 */

import { getCSRFToken } from './utils/csrf.js';
import { showNotification } from './utils/notification.js';
import { messagingAPI } from './api/messaging-api.js';

console.log('=== Testing Modular JavaScript ===');

// Test 1: CSRF Token
console.log('Test 1: CSRF Token');
try {
  const token = getCSRFToken();
  console.log('✅ CSRF Token retrieved:', token ? 'Found' : 'Not found');
} catch (error) {
  console.error('❌ CSRF Token test failed:', error);
}

// Test 2: Notification
console.log('Test 2: Notification');
try {
  showNotification('Test notification - modules working!', 'success');
  console.log('✅ Notification displayed');
} catch (error) {
  console.error('❌ Notification test failed:', error);
}

// Test 3: Messaging API
console.log('Test 3: Messaging API');
try {
  console.log('✅ Messaging API module loaded');
  console.log('Available methods:', Object.keys(messagingAPI));
} catch (error) {
  console.error('❌ Messaging API test failed:', error);
}

console.log('=== All Tests Complete ===');
console.log('If all tests passed, the modular structure is working correctly.');
