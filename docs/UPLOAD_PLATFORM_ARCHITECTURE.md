# PwaniNet Upload Platform Architecture

## Overview

The PwaniNet Upload Platform is a modular JavaScript subsystem that wraps the existing Django posting pipeline without replacing it. It introduces a robust upload engine that future features can build upon while preserving all existing functionality.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Upload Manager                          │
│                    (Single Source of Truth)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├─→ State Machine Factory
                              │   └─→ UploadStateMachine (per upload)
                              │       ├─→ IDLE
                              │       ├─→ PREPARING
                              │       ├─→ VALIDATING
                              │       ├─→ READING_MEDIA
                              │       ├─→ GENERATING_PREVIEW
                              │       ├─→ COMPRESSING_IMAGES
                              │       ├─→ READY
                              │       ├─→ QUEUED
                              │       ├─→ UPLOADING
                              │       ├─→ SERVER_PROCESSING
                              │       ├─→ PUBLISHED
                              │       ├─→ FAILED
                              │       └─→ CANCELLED
                              │
                              ├─→ Upload Queue
                              │   └─→ Sequential processing
                              │       ├─→ Queue management
                              │       ├─→ Cancel
                              │       ├─→ Retry
                              │       └─→ Remove failed
                              │
                              ├─→ Progress Manager
                              │   └─→ ProgressTracker (per upload)
                              │       ├─→ Validation progress
                              │       ├─→ Compression progress
                              │       ├─→ Upload progress
                              │       ├─→ Server processing progress
                              │       └─→ Publication progress
                              │
                              ├─→ Upload Validator
                              │   ├─→ ImageValidator
                              │   ├─→ VideoValidator
                              │   ├─→ DocumentValidator
                              │   ├─→ AudioValidator
                              │   └─→ CaptionValidator
                              │
                              ├─→ Image Compressor
                              │   └─→ Client-side compression (>2MB)
                              │       ├─→ Resize to 1920x1920
                              │       └─→ JPEG 85% quality
                              │
                              ├─→ Preview Manager
                              │   └─→ URL.createObjectURL() based
                              │       ├─→ Image previews
                              │       ├─→ Video previews
                              │       ├─→ Document previews
                              │       └─→ Audio previews
                              │
                              ├─→ Upload API
                              │   └─→ Django communication
                              │       ├─→ FormData creation
                              │       ├─→ CSRF handling
                              │       ├─→ XHR with progress
                              │       └─→ Response parsing
                              │
                              └─→ Upload UI
                                  └─→ Global upload banner
                                      ├─→ Current stage
                                      ├─→ Overall progress
                                      ├─→ Current file
                                      ├─→ Files completed
                                      ├─→ Estimated time
                                      └─→ Cancel button
```

## Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Upload Events Bus                         │
│                          (upload_events.js)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Upload Manager│   │ Upload UI     │   │ Other Modules │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        ├─→ UPLOAD_ADDED     ├─→ STATE_CHANGED    │
        ├─→ UPLOAD_REMOVED   ├─→ PROGRESS_UPDATED │
        ├─→ UPLOAD_STARTED   ├─→ VALIDATION_...   │
        ├─→ UPLOAD_COMPLETED ├─→ COMPRESSION_...  │
        ├─→ UPLOAD_FAILED    ├─→ UPLOAD_PROGRESS  │
        ├─→ UPLOAD_CANCELLED │                     │
        └─→ UPLOAD_RETRIED   │                     │
```

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser Storage Layer                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  IndexedDB    │   │     OPFS      │   │    Cache API  │
│               │   │ (Origin       │   │               │
│ ┌─────────────┐│   │  Private     │   │ ┌─────────────┐│
│ │ Drafts      ││   │  File System)│   │ │ Image Cache ││
│ │ Downloads   ││   │               │   │ │ Video Cache ││
│ │ Temp Data   ││   │ ┌─────────────┐│   │ │ API Cache   ││
│ └─────────────┘│   │ │ Downloads   ││   │ └─────────────┘│
└───────────────┘   │ └─────────────┘│   └───────────────┘
                    └───────────────┘
```

## Downloads Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Downloads Manager                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├─→ OPFS (Primary)
                              │   └─→ Origin Private File System
                              │       ├─→ File handles
                              │       ├─→ Direct file access
                              │       └─→ Better performance
                              │
                              └─→ IndexedDB (Fallback)
                                  └─→ Blob storage
                                      ├─→ Metadata in IndexedDB
                                      ├─→ Blobs in separate store
                                      └─→ Broader compatibility
```

## File Structure

```
static/js/upload/
├── upload_events.js           # Event bus and event names
├── upload_state_machine.js    # State management per upload
├── upload_validator.js        # Validation logic
├── image_compression.js       # Client-side image compression
├── preview_manager.js         # Preview generation
├── upload_api.js              # Django communication
├── upload_queue.js            # Queue management
├── upload_progress.js         # Progress tracking
├── upload_manager.js          # Orchestration layer
├── upload_ui.js               # Banner and UI components
├── indexeddb_manager.js       # IndexedDB operations
├── cache_manager.js           # Cache management
├── storage_manager.js         # Storage estimation
└── downloads_manager.js       # Downloads management
```

## Browser Compatibility Matrix

| Feature                    | Chrome | Firefox | Safari | Edge | Fallback |
|----------------------------|--------|---------|--------|------|----------|
| Storage Estimate API       | ✅     | ✅      | ✅     | ✅   | ❌       |
| Origin Private File System | ✅     | ❌      | ❌     | ✅   | IndexedDB |
| IndexedDB                  | ✅     | ✅      | ✅     | ✅   | ❌       |
| Cache API                  | ✅     | ✅      | ✅     | ✅   | ❌       |
| Web Share API              | ✅     | ✅      | ✅     | ✅   | Hide button |
| URL.createObjectURL()      | ✅     | ✅      | ✅     | ✅   | FileReader |

## Integration Points

### Existing Functionality Modified

1. **create_post.html**
   - Added upload platform module imports
   - Initialized uploadManager, uploadUI, and draftManager
   - Exposed uploadManager to global scope for future integration

2. **post_card.html**
   - Added download buttons to media elements (images, videos, audio)
   - Added CSS for download button styling
   - Added downloadsManager integration for download functionality
   - Fallback to direct download if downloadsManager unavailable

### Existing Functionality Preserved

- Django models unchanged
- MEDIA_ROOT structure unchanged
- Post rendering unchanged
- Media rendering unchanged (only added download buttons)
- HTMX feed updates unchanged
- Existing upload endpoint behavior unchanged
- Form submission logic unchanged

## Remaining Placeholders

The following features are architecturally supported but intentionally unimplemented:

1. **Video Compression**
   - Placeholder in image_compression.js
   - Not implemented per requirements
   - Architecture supports future implementation

2. **Offline Uploads**
   - Placeholder in upload_manager.js
   - Not implemented per requirements
   - Architecture supports future implementation with Service Workers

3. **Resumable Uploads**
   - Placeholder in upload_api.js
   - Not implemented per requirements
   - Architecture supports future implementation with chunked uploads

## Key Design Decisions

1. **Modular Architecture**
   - Each module is self-contained
   - Communication via event bus
   - Easy to test and maintain

2. **Backwards Compatibility**
   - Wraps existing Django pipeline
   - Does not modify core functionality
   - Existing forms and views unchanged

3. **Performance**
   - Client-side compression reduces bandwidth
   - URL.createObjectURL() for previews
   - Lazy-loading of downloads
   - Object URL cleanup

4. **User Experience**
   - Global upload banner
   - Real-time progress tracking
   - Graceful error handling
   - No blocking modals or alerts

## State Machine Transitions

```
IDLE → PREPARING → VALIDATING → READING_MEDIA → GENERATING_PREVIEW 
→ COMPRESSING_IMAGES → READY → QUEUED → UPLOADING → SERVER_PROCESSING 
→ PUBLISHED

Any state → FAILED (on error)
Any state → CANCELLED (on user cancel)
FAILED → QUEUED (on retry)
```

## Upload Lifecycle

1. **User selects files** → Upload created
2. **Validation** → Files checked for size, type, dimensions
3. **Preview generation** → URL.createObjectURL() for previews
4. **Compression** → Images >2MB compressed client-side
5. **Queue** → Upload added to sequential queue
6. **Upload** → XHR to Django with progress tracking
7. **Server processing** → Django handles media processing
8. **Publication** → Post published to feed
9. **Cleanup** → Object URLs revoked, temp data cleared

## Error Handling

- Network failure → Retry mechanism (max 3 retries)
- Validation failure → Structured error messages
- Compression failure → Fallback to original file
- Storage quota exceeded → User notification
- Browser API unsupported → Graceful fallback
- Server error → Error banner with retry option

## Security Considerations

- CSRF token handling in UploadAPI
- File type validation on client and server
- File size limits enforced
- No execution of uploaded files
- Sanitized metadata storage

## Performance Optimizations

- Client-side image compression
- Sequential uploads (no parallelism yet)
- Lazy-load previews
- Object URL reuse and cleanup
- Efficient event handling
- Minimal memory copies

## Testing Recommendations

1. **Unit Tests**
   - Each module independently
   - State machine transitions
   - Validation logic
   - Compression algorithms

2. **Integration Tests**
   - Upload lifecycle end-to-end
   - Queue management
   - Progress tracking
   - Error scenarios

3. **Backward Compatibility Tests**
   - Existing post creation flow
   - Form submission
   - Media rendering
   - HTMX interactions

## Deployment Notes

1. **Static Files**
   - All upload modules in `static/js/upload/`
   - Ensure proper MIME types for .js files
   - Consider bundling for production

2. **Browser Support**
   - Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
   - Graceful degradation for older browsers
   - Feature detection before using APIs

3. **Monitoring**githu
   - Track upload success/failure rates
   - Monitor compression ratios
   - Track storage usage
   - Monitor queue performance

## Future Enhancements

1. **Parallel Uploads**
   - Add concurrent upload option
   - Bandwidth management
   - Priority queuing

2. **Resumable Uploads**
   - Chunked upload support
   - Pause/resume functionality
   - Better handling of network interruptions

3. **Video Compression**
   - Client-side video compression
   - Format conversion
   - Thumbnail generation

4. **Offline Support**
   - Service Worker integration
   - Background sync
   - Offline queue

5. **Advanced Storage**
   - Quota management
   - Automatic cleanup
   - Storage optimization

## Summary

The PwaniNet Upload Platform successfully introduces a modular, extensible upload engine while maintaining complete backward compatibility with the existing Django posting pipeline. The architecture is designed for future enhancements and provides a solid foundation for advanced upload features.
