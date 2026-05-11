/**
 * Wallpaper Service
 * Manages wallpaper caching and loading for conversations
 */

export class WallpaperService {
  constructor() {
    this.cacheDuration = 24 * 60 * 60 * 1000; // 24 hours
  }

  /**
   * Initialize wallpaper service for a conversation
   * @param {number} conversationId - Conversation ID
   */
  init(conversationId) {
    this.checkDeviceFingerprint();
    this.loadWallpaperWithCache(conversationId);
  }

  /**
   * Get cache key for wallpaper data
   * @param {number} conversationId - Conversation ID
   * @param {string} type - Cache type
   * @returns {string} Cache key
   */
  getCacheKey(conversationId, type) {
    return `chatWallpaper_${conversationId}_${type}`;
  }

  /**
   * Get device fingerprint
   * @returns {string} Device fingerprint
   */
  getDeviceFingerprint() {
    return navigator.userAgent + 
           navigator.language + 
           screen.width + 'x' + screen.height;
  }

  /**
   * Check if this is a new device and clear caches if needed
   * @returns {boolean} True if new device
   */
  checkDeviceFingerprint() {
    const deviceKey = 'deviceFingerprint';
    const storedFingerprint = localStorage.getItem(deviceKey);
    const currentFingerprint = this.getDeviceFingerprint();
    
    if (storedFingerprint !== currentFingerprint) {
      this.clearAllWallpaperCaches();
      localStorage.setItem(deviceKey, currentFingerprint);
      return true;
    }
    
    return false;
  }

  /**
   * Clear all wallpaper caches
   */
  clearAllWallpaperCaches() {
    Object.keys(localStorage)
      .filter(key => key.startsWith('chatWallpaper_') || 
                    key.startsWith('cacheTimestamp_'))
      .forEach(key => localStorage.removeItem(key));
    
    console.log('🧹 Cleared wallpaper caches for new device');
  }

  /**
   * Load wallpaper with caching
   * @param {number} conversationId - Conversation ID
   */
  async loadWallpaperWithCache(conversationId) {
    const cacheKey = this.getCacheKey(conversationId, 'data');
    const timestampKey = this.getCacheKey(conversationId, 'timestamp');
    
    // Check cache first
    const cachedWallpaper = localStorage.getItem(cacheKey);
    const cacheTimestamp = localStorage.getItem(timestampKey);
    
    const isCacheValid = cachedWallpaper && 
                        cacheTimestamp && 
                        (Date.now() - parseInt(cacheTimestamp)) < this.cacheDuration;
    
    if (isCacheValid) {
      console.log('🎯 Loading wallpaper from cache');
      this.applyWallpaper(cachedWallpaper);
      return cachedWallpaper;
    }
    
    // Cache miss or expired - fetch from DB
    console.log('🔄 Cache miss - fetching from DB');
    try {
      const response = await fetch(`/api/messaging/themes/?conversation=${conversationId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch theme');
      }
      
      const data = await response.json();
      const theme = data.results?.[0];
      
      if (theme && theme.theme_type === 'image' && theme.light_image_url) {
        // Cache the wallpaper URL
        localStorage.setItem(cacheKey, theme.light_image_url);
        localStorage.setItem(timestampKey, Date.now().toString());
        
        this.applyWallpaper(theme.light_image_url);
        console.log('✅ Wallpaper loaded from DB and cached');
        return theme.light_image_url;
      }
    } catch (error) {
      console.error('Failed to fetch wallpaper from DB:', error);
    }
    
    // Fallback to per-conversation localStorage
    const conversationWallpaper = localStorage.getItem(`chatWallpaper_${conversationId}`);
    if (conversationWallpaper) {
      console.log('🔄 Using conversation wallpaper from localStorage');
      this.applyWallpaper(conversationWallpaper);
      return conversationWallpaper;
    }
    
    return null;
  }

  /**
   * Apply wallpaper to messages area
   * @param {string} wallpaperUrl - Wallpaper URL
   */
  applyWallpaper(wallpaperUrl) {
    const messagesArea = document.getElementById('messagesContainer');
    if (messagesArea && wallpaperUrl) {
      messagesArea.style.backgroundImage = `url(${wallpaperUrl})`;
      messagesArea.style.backgroundSize = 'cover';
      messagesArea.style.backgroundPosition = 'center';
      console.log('🎨 Wallpaper applied:', wallpaperUrl);
    }
  }

  /**
   * Get CSRF token
   * @returns {string} CSRF token
   */
  getCSRFToken() {
    const tokenFromInput = document.querySelector('[name="csrfmiddlewaretoken"]');
    const tokenFromMeta = document.querySelector('meta[name="csrf-token"]');
    
    if (tokenFromInput) return tokenFromInput.value;
    if (tokenFromMeta) return tokenFromMeta.content;
    
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    if (cookieValue) return cookieValue;
    
    return '';
  }

  /**
   * Update wallpaper cache
   * @param {number} conversationId - Conversation ID
   * @param {string} wallpaperUrl - Wallpaper URL
   */
  async updateWallpaperCache(conversationId, wallpaperUrl) {
    const cacheKey = this.getCacheKey(conversationId, 'data');
    const timestampKey = this.getCacheKey(conversationId, 'timestamp');
    
    // Update cache
    localStorage.setItem(cacheKey, wallpaperUrl);
    localStorage.setItem(timestampKey, Date.now().toString());
    
    console.log('✅ Wallpaper cache updated for conversation:', conversationId);
  }

  /**
   * Clear wallpaper cache for conversation
   * @param {number} conversationId - Conversation ID
   */
  clearWallpaperCache(conversationId) {
    const cacheKey = this.getCacheKey(conversationId, 'data');
    const timestampKey = this.getCacheKey(conversationId, 'timestamp');
    
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(timestampKey);
    
    console.log('🧹 Wallpaper cache cleared for conversation:', conversationId);
  }
}

// Create global instance
export const wallpaperService = new WallpaperService();
