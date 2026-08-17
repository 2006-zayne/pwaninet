/**
 * Notification Center JavaScript Module
 * Handles filter changes, search, UI interactions, and HTMX event listeners
 */

/**
 * Handle search input with debouncing
 * Searches notifications and updates URL
 */
let searchTimeout;
export function handleSearch(event) {
  const searchInput = document.getElementById('search-input');
  const query = searchInput.value.trim();
  
  // Clear previous timeout
  clearTimeout(searchTimeout);
  
  // Debounce search (wait 500ms after user stops typing)
  searchTimeout = setTimeout(() => {
    const url = new URL(window.location);
    
    // Update or remove search parameter
    if (query) {
      url.searchParams.set('search', query);
    } else {
      url.searchParams.delete('search');
    }
    
    window.location.href = url.toString();
  }, 500);
}

/**
 * Handle filter dropdown changes
 * Updates URL with selected filter parameters and reloads page
 */
export function handleFilterChange() {
  const select = document.getElementById('filter-select');
  const value = select.value;
  
  if (value === '') {
    // Go to base URL (all notifications)
    window.location.href = window.location.pathname;
  } else {
    // Build URL with parameters
    const url = new URL(window.location);
    
    // Clear existing parameters
    url.searchParams.delete('type');
    url.searchParams.delete('read');
    url.searchParams.delete('time');
    url.searchParams.delete('grouped');
    url.searchParams.delete('sender_grouped');
    url.searchParams.delete('hybrid_grouped');
    
    // Add new parameter
    const [key, val] = value.split('=');
    url.searchParams.set(key, val);
    
    window.location.href = url.toString();
  }
}

/**
 * Apply quick filter from filter chips
 */
export function applyQuickFilter(filterValue) {
  const url = new URL(window.location);
  
  // Clear existing filter parameters
  url.searchParams.delete('type');
  url.searchParams.delete('read');
  url.searchParams.delete('time');
  url.searchParams.delete('grouped');
  url.searchParams.delete('sender_grouped');
  url.searchParams.delete('hybrid_grouped');
  
  // Add new filter
  const [key, val] = filterValue.split('=');
  url.searchParams.set(key, val);
  
  window.location.href = url.toString();
}

/**
 * Clear search query
 */
export function clearSearch() {
  const url = new URL(window.location);
  url.searchParams.delete('search');
  window.location.href = url.toString();
}

/**
 * Toggle visibility of older notifications section
 * Used for time-grouped notifications to show/hide older items
 */
export function toggleOlderNotifications() {
  const olderSection = document.getElementById('older-section');
  const viewMoreBtn = document.querySelector('.btn-view-more');
  
  if (olderSection.style.display === 'none') {
    olderSection.style.display = 'block';
    viewMoreBtn.innerHTML = '<i class="bi bi-chevron-up"></i> View less';
    viewMoreBtn.classList.add('expanded');
  } else {
    olderSection.style.display = 'none';
    viewMoreBtn.innerHTML = '<i class="bi bi-chevron-down"></i> View more';
    viewMoreBtn.classList.remove('expanded');
  }
}

/**
 * Initialize HTMX event listeners
 * Handles unread count updates after HTMX swaps
 */
export function initHtmxListeners() {
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.triggerSpec?.trigger === 'updateUnreadCount') {
      // Update unread count badge
      fetch('/notifications/unread-count/')
        .then(r => r.text())
        .then(html => {
          const badge = document.getElementById('unread-count-badge');
          if (badge) badge.outerHTML = html;
        });
      
      // Update group unread badges via API
      fetch('/groups/api/unread-counts/')
        .then(r => r.json())
        .then(counts => {
          document.querySelectorAll('.unread-badge').forEach(badge => {
            const groupId = badge.getAttribute('data-group-id');
            if (groupId && counts[groupId] !== undefined) {
              const count = counts[groupId];
              if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline-flex';
                // Add pulse animation
                badge.classList.add('pulsing');
                setTimeout(() => badge.classList.remove('pulsing'), 600);
              } else {
                badge.style.display = 'none';
              }
            }
          });
        });
    }
  });
  
  // Add arrival animation to new notifications
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'notification-list') {
      const newItems = evt.detail.target.querySelectorAll('.notif-item');
      newItems.forEach((item, index) => {
        // Stagger animations
        setTimeout(() => {
          item.classList.add('arriving');
          setTimeout(() => item.classList.remove('arriving'), 400);
        }, index * 50);
      });
    }
  });
  
  // Add dismissal animation before deletion
  document.body.addEventListener('htmx:beforeRequest', function(evt) {
    const target = evt.detail.target;
    if (target && target.classList.contains('notif-item')) {
      const isDelete = evt.detail.requestConfig?.headers?.includes('delete') ||
                       evt.detail.requestConfig?.verb === 'delete';
      if (isDelete) {
        target.classList.add('dismissing');
        // Delay the request to allow animation to play
        evt.preventDefault();
        setTimeout(() => {
          htmx.trigger(evt.detail.elt, evt.detail.triggerSpec);
        }, 300);
      }
    }
  });
}

/**
 * Initialize notification center
 * Call this on page load to set up all event listeners
 */
export function initNotificationCenter() {
  // Make functions available globally for inline event handlers
  window.handleFilterChange = handleFilterChange;
  window.toggleOlderNotifications = toggleOlderNotifications;
  window.handleSearch = handleSearch;
  window.applyQuickFilter = applyQuickFilter;
  window.clearSearch = clearSearch;
  window.toggleSelection = toggleSelection;
  window.selectAllNotifications = selectAllNotifications;
  window.deselectAllNotifications = deselectAllNotifications;
  window.toggleSelectionMode = toggleSelectionMode;
  window.markSelectedAsRead = markSelectedAsRead;
  window.deleteSelected = deleteSelected;
  window.loadMoreNotifications = loadMoreNotifications;
  
  // Initialize HTMX listeners
  initHtmxListeners();
  
  // Initialize lazy loading
  initLazyLoading();
}

/**
 * Initialize lazy loading for notifications
 */
export function initLazyLoading() {
  const loadMoreTrigger = document.getElementById('load-more-trigger');
  
  if (loadMoreTrigger) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && loadMoreTrigger.dataset.loading !== 'true') {
          loadMoreNotifications();
        }
      });
    }, {
      rootMargin: '200px',
      threshold: 0.1
    });
    
    observer.observe(loadMoreTrigger);
  }
}

/**
 * Load more notifications via infinite scroll with cursor-based pagination
 */
export function loadMoreNotifications() {
  const loadMoreTrigger = document.getElementById('load-more-trigger');
  const currentCursor = loadMoreTrigger.dataset.cursor || '';
  
  // Prevent duplicate requests
  if (loadMoreTrigger.dataset.loading === 'true') {
    return;
  }
  
  loadMoreTrigger.dataset.loading = 'true';
  
  // Show loading indicator
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    loadingIndicator.style.display = 'block';
  }
  
  // Get current URL parameters
  const url = new URL(window.location);
  if (currentCursor) {
    url.searchParams.set('cursor', currentCursor);
  }
  url.searchParams.set('partial', 'true');
  url.searchParams.set('limit', '10');
  
  // Fetch next page with cursor
  fetch(url.toString())
    .then(response => response.json())
    .then(data => {
      if (data.html && data.html.trim()) {
        // Append new notifications with time sections
        const notificationList = document.getElementById('notification-list');
        const cardBody = notificationList.querySelector('.card-body');
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = data.html;
        
        // Check for duplicate time sections and merge them
        const newTimeSections = tempDiv.querySelectorAll('.time-section');
        const existingTimeSections = cardBody.querySelectorAll('.time-section');
        
        newTimeSections.forEach(newSection => {
          const newHeader = newSection.querySelector('.time-section-header h6');
          if (!newHeader) return;
          
          const newHeaderText = newHeader.textContent.trim();
          let shouldAppend = true;
          
          // Check if this time section already exists
          existingTimeSections.forEach(existingSection => {
            const existingHeader = existingSection.querySelector('.time-section-header h6');
            if (existingHeader && existingHeader.textContent.trim() === newHeaderText) {
              // Append only the notification items, not the section header
              const newItems = newSection.querySelectorAll('.list-group-item');
              newItems.forEach(item => {
                item.classList.add('arriving');
                setTimeout(() => item.classList.remove('arriving'), 400);
                existingSection.appendChild(item);
              });
              shouldAppend = false;
            }
          });
          
          // If section doesn't exist, append the whole section
          if (shouldAppend) {
            const newItems = newSection.querySelectorAll('.list-group-item');
            newItems.forEach((item, index) => {
              item.classList.add('arriving');
              setTimeout(() => item.classList.remove('arriving'), 400);
            });
            cardBody.appendChild(newSection);
          }
        });
        
        // Clean up tempDiv
        tempDiv.remove();
        
        // Update cursor for next request
        if (data.next_cursor) {
          loadMoreTrigger.dataset.cursor = data.next_cursor;
        } else {
          // No more items, hide trigger
          loadMoreTrigger.style.display = 'none';
        }
        
        // Check if there are more items
        if (!data.has_more) {
          loadMoreTrigger.style.display = 'none';
        }
      } else {
        // No more notifications
        loadMoreTrigger.style.display = 'none';
      }
    })
    .catch(error => {
      console.error('Error loading more notifications:', error);
    })
    .finally(() => {
      loadMoreTrigger.dataset.loading = 'false';
      if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
      }
    });
}

/**
 * Toggle selection of a notification
 */
export function toggleSelection(notificationId) {
  const checkbox = document.getElementById(`select-${notificationId}`);
  const card = checkbox.closest('.notif-item');
  
  if (checkbox.checked) {
    card.classList.add('selected');
  } else {
    card.classList.remove('selected');
  }
  
  updateBulkActionButtons();
}

/**
 * Select all notifications
 */
export function selectAllNotifications() {
  const checkboxes = document.querySelectorAll('.notification-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = true;
    const card = checkbox.closest('.notif-item');
    if (card) card.classList.add('selected');
  });
  updateBulkActionButtons();
}

/**
 * Deselect all notifications
 */
export function deselectAllNotifications() {
  const checkboxes = document.querySelectorAll('.notification-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = false;
    const card = checkbox.closest('.notif-item');
    if (card) card.classList.remove('selected');
  });
  updateBulkActionButtons();
}

/**
 * Update bulk action buttons visibility based on selection
 */
export function updateBulkActionButtons() {
  const selectedCount = document.querySelectorAll('.notification-checkbox:checked').length;
  const bulkActionBar = document.getElementById('selection-mode-bar');
  
  if (bulkActionBar) {
    if (selectedCount > 0) {
      bulkActionBar.classList.add('active');
      bulkActionBar.querySelector('.selected-count').textContent = `${selectedCount} selected`;
    } else {
      bulkActionBar.classList.remove('active');
    }
  }
}

/**
 * Toggle selection mode
 */
export function toggleSelectionMode() {
  const selectionBar = document.getElementById('selection-mode-bar');
  const checkboxes = document.querySelectorAll('.notification-checkbox');
  
  if (selectionBar.classList.contains('active')) {
    // Exit selection mode
    selectionBar.classList.remove('active');
    checkboxes.forEach(cb => {
      cb.checked = false;
      cb.style.display = 'none';
      const card = cb.closest('.notif-item');
      if (card) card.classList.remove('selected');
    });
  } else {
    // Enter selection mode
    selectionBar.classList.add('active');
    checkboxes.forEach(cb => {
      cb.style.display = 'block';
    });
  }
}

/**
 * Mark selected notifications as read
 */
export function markSelectedAsRead() {
  const selectedIds = [];
  document.querySelectorAll('.notification-checkbox:checked').forEach(checkbox => {
    selectedIds.push(checkbox.dataset.notificationId);
  });
  
  if (selectedIds.length === 0) return;
  
  // Send bulk action request
  fetch('/notifications/bulk-action/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      action: 'mark_read',
      notification_ids: selectedIds
    })
  }).then(response => response.json())
    .then(data => {
      if (data.success) {
        // Reload page to show updated state
        window.location.reload();
      }
    });
}

/**
 * Delete selected notifications
 */
export function deleteSelected() {
  const selectedIds = [];
  document.querySelectorAll('.notification-checkbox:checked').forEach(checkbox => {
    selectedIds.push(checkbox.dataset.notificationId);
  });
  
  if (selectedIds.length === 0) return;
  
  if (!confirm(`Delete ${selectedIds.length} notification(s)?`)) return;
  
  // Send bulk action request
  fetch('/notifications/bulk-action/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      action: 'delete',
      notification_ids: selectedIds
    })
  }).then(response => response.json())
    .then(data => {
      if (data.success) {
        // Reload page to show updated state
        window.location.reload();
      }
    });
}

/**
 * Get CSRF token from cookie
 */
function getCsrfToken() {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return decodeURIComponent(value);
    }
  }
  return '';
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initNotificationCenter);
} else {
  initNotificationCenter();
}
