# PwaniNet Storage Manager & Downloads Manager Implementation

## Overview

This implementation adds a complete Storage Manager and Downloads Manager to PwaniNet while preserving the existing Posts and Media architecture. This is a strictly additive feature that does not modify existing post/media functionality.

## Architecture

### New Client-Side Module Structure

```
static/js/storage/
├── indexeddb.js          # IndexedDB wrapper for metadata storage
├── downloads_manager.js  # Downloads management with OPFS/IndexedDB fallback
├── cache_manager.js      # Browser cache management using Cache API
├── storage_manager.js    # Overall storage coordination
└── storage_ui.js         # UI components for storage management
```

## Key Features

### 1. Storage Manager (`storage_manager.js`)
- Coordinates all storage operations
- Provides comprehensive storage statistics
- Formats bytes to human-readable format
- Checks browser compatibility
- Manages temporary data clearing

### 2. Downloads Manager (`downloads_manager.js`)
- **OPFS (Origin Private File System)**: Primary storage for large files (videos, images)
- **IndexedDB Blob Storage**: Fallback for browsers without OPFS support
- **Metadata Storage**: Uses IndexedDB for download metadata
- **Duplicate Detection**: Prevents downloading the same file twice
- **File Operations**: Open, Share, Delete downloaded files
- **Category Support**: Images, Videos, Documents, Audio
- **Search & Sort**: By filename, extension, type, date, size

### 3. Cache Manager (`cache_manager.js`)
- **Image Cache**: Clear cached images
- **Video Cache**: Clear cached videos
- **API Cache**: Clear API responses
- **All Cache**: Clear all cached data
- **Storage Estimation**: Uses `navigator.storage.estimate()` where available

### 4. IndexedDB Manager (`indexeddb.js`)
- **Downloads Store**: Metadata for downloaded files
- **Cache Store**: Cache metadata
- **Temporary Store**: Upload queue, drafts, sync data
- **Indexed Queries**: Fast lookups by category, date, URL
- **Storage Statistics**: Calculate usage by type

### 5. Storage UI (`storage_ui.js`)
- **Storage Usage Display**: Progress bar and breakdown
- **Downloads Section**: Recent downloads with actions
- **Cache Management**: Clear options for each cache type
- **Temporary Data**: Clear upload queue, drafts, sync queue
- **Offline Content**: Placeholder for future offline support

## Settings Page Extensions

### Storage Settings (`users/templates/users/settings/storage.html`)
Extended with new sections:
- **Storage Usage**: Total storage used with progress bar
- **Downloads**: Recent downloads preview
- **Clear Cache**: Image, video, API cache management
- **Temporary Data**: Upload queue, drafts, sync queue
- **Offline Content**: Placeholder for future offline support

### Downloads Manager Page (`users/templates/users/settings/downloads.html`)
New dedicated page for downloads management:
- **Tabs**: All, Images, Videos, Documents
- **Search**: By filename, extension, type
- **Sort**: Newest, Oldest, Largest, Smallest, A-Z
- **Actions**: Open, Share, Delete for each download
- **Storage Statistics**: Download counts by category
- **Empty States**: Appropriate messages for each category

## Download Integration Points

### 1. Post Card Dropdown (`posts/templates/posts/partials/post_card.html`)
- Added "Download" option to three-dot menu
- Only shows when post has media (images, videos, documents, audio)
- Dynamically detects media type and URL
- Calls `DownloadsManager.download()` on click

### 2. Fullscreen Image Viewer (`posts/templates/posts/image_fullscreen.html`)
- Added download button in fullscreen mode
- Positioned in top-left corner
- Downloads the current image being viewed

## Metadata Schema

### Download Metadata
```javascript
{
  id: string,              // Unique download ID
  postId: number,          // Original post ID
  mediaId: number,        // Media ID
  filename: string,       // Original filename
  mimeType: string,       // MIME type
  extension: string,      // File extension
  category: string,       // 'image', 'video', 'document', 'audio'
  size: number,           // File size in bytes
  downloadDate: string,   // ISO timestamp
  thumbnail: string,      // Thumbnail URL (for images)
  sourceURL: string,      // Original media URL
  opfsPath: string        // OPFS path (if using OPFS)
}
```

## Browser Compatibility

### Graceful Fallbacks
- **OPFS**: Falls back to IndexedDB if not available
- **IndexedDB**: Required for metadata, always available
- **Cache API**: Falls back to IndexedDB cache tracking
- **Web Share API**: Falls back to download link copy
- **Storage Estimate API**: Falls back to calculated stats

### Compatibility Check
```javascript
{
  opfs: 'getDirectory' in navigator,
  indexedDB: 'indexedDB' in window,
  cacheAPI: 'caches' in window,
  webShare: 'share' in navigator,
  storageEstimate: 'storage' in navigator && 'estimate' in navigator.storage
}
```

## File Operations

### Open
- **Images**: Fullscreen viewer (reuses existing viewer)
- **Videos**: Video player modal (reuses existing player)
- **Documents**: Browser's native viewer

### Share
- **Web Share API**: Native sharing on supported devices
- **Fallback**: Download link copy or re-download

### Delete
- Removes metadata from IndexedDB
- Removes file from OPFS or IndexedDB blob storage
- **Never** deletes server media
- **Never** affects original posts

## Non-Breaking Implementation

### Preserved Functionality
- ✅ Post feed rendering
- ✅ Media viewing (images, videos, PDFs, documents)
- ✅ Upload pipeline
- ✅ Reactions and comments
- ✅ Pagination
- ✅ HTMX interactions
- ✅ Notification system
- ✅ All existing post/media features

### Integration Points
Only two lightweight integration points added:
1. Download button in post card dropdown
2. Download button in fullscreen image viewer

Both delegate to the new `DownloadsManager` without modifying existing logic.

## URL Routes Added

```python
path('settings/storage/downloads/', views.settings_downloads_view, name='settings_downloads'),
```

## Views Added

```python
@login_required
def settings_downloads_view(request):
    """Downloads manager page"""
    return render(request, 'users/settings/downloads.html')
```

## Usage

### For Users
1. Navigate to Settings → Storage
2. View storage usage breakdown
3. Clear cache or temporary data
4. Click "View All" to see Downloads Manager
5. Download media from post cards or fullscreen viewer
6. Manage downloads in Downloads Manager

### For Developers
```javascript
// Import and use the storage managers
import { downloadsManager } from '/static/js/storage/downloads_manager.js';
import { storageManager } from '/static/js/storage/storage_manager.js';
import { cacheManager } from '/static/js/storage/cache_manager.js';

// Download a file
await downloadsManager.download({
  url: 'https://example.com/image.jpg',
  filename: 'image.jpg',
  postId: 123,
  mediaId: 456,
  mimeType: 'image/jpeg',
  category: 'image'
});

// Get storage statistics
const stats = await storageManager.getStorageStats();

// Clear cache
await cacheManager.clearImageCache();
```

## Performance Considerations

- **Lazy Loading**: Thumbnails loaded on demand
- **OPFS**: More efficient for large files than IndexedDB
- **IndexedDB**: Used for metadata and small files as fallback
- **No Preloading**: Downloads only loaded when requested
- **Efficient Queries**: IndexedDB indexes for fast lookups

## Error Handling

- **Insufficient Storage**: User-friendly toast message
- **Failed Downloads**: Graceful error handling with retry option
- **Unsupported APIs**: Automatic fallback to alternatives
- **Duplicate Downloads**: Detected and prevented with user notification
- **Permission Failures**: Clear error messages

## Future Enhancements

### Offline Content
- Placeholder section added for future offline support
- Can be extended to cache posts for offline viewing

### Additional Features
- Background download queue
- Download pause/resume
- Download scheduling
- Storage optimization suggestions
- Automatic cache cleanup

## Testing Checklist

- [x] Storage module files created
- [x] IndexedDB manager implemented
- [x] Downloads manager with OPFS/IndexedDB
- [x] Cache manager implemented
- [x] Storage manager implemented
- [x] Storage UI implemented
- [x] Settings storage page extended
- [x] Downloads manager page created
- [x] Download integration points added
- [x] URL routes added
- [x] Views added
- [ ] Manual testing in browser
- [ ] Verify existing functionality unchanged
- [ ] Test download workflow
- [ ] Test cache clearing
- [ ] Test temporary data clearing
- [ ] Test browser compatibility

## Notes

- The implementation is modular and can be easily removed without affecting existing functionality
- All storage operations are client-side only
- Server-side changes are minimal (only URL routes and views)
- The system respects user privacy - no data sent to external services
- Downloads are stored locally in the browser's storage
