# Pwaninet Feature Implementation Roadmap

This document tracks all planned features and improvements to be added to Pwaninet. Features are organized by priority and category with checkboxes to track implementation progress.

## Legend
- [ ] Not started
- [x] Completed
- [~] In progress

---

## Phase 1: Critical Technical Debt

**Status:** ✅ COMPLETE

### 1.1 Complete Domain Migration
- [x] Move all views from `core/views.py` to respective domain apps
  - [x] Move user-related views to `users/views.py`
  - [x] Move post-related views to `posts/views.py`
  - [x] Move group-related views to `groups/views.py`
  - [x] Move notification-related views to `notifications/views.py`
- [x] Move all forms from `core/forms.py` to respective domain apps
- [x] Remove deprecated `core` app entirely
- [x] Update all imports across the codebase
- [x] Add comprehensive `admin.py` for each domain app
- [x] Test all migrated functionality

**Implementation Notes:**
- Start with one domain app at a time
- Run tests after each migration
- Update URL patterns as needed
- Ensure backward compatibility during transition

**Status:** ✅ COMPLETE - Core app doesn't exist, all views/forms already in domain apps

---

### 1.2 Testing Infrastructure
- [x] Set up test framework (pytest or Django's test framework)
- [x] Write unit tests for `users` domain
  - [x] User model tests
  - [x] Follow model tests
  - [x] Profile service tests
  - [x] Friend suggestion service tests
- [x] Write unit tests for `posts` domain
  - [x] Post model tests
  - [x] Like/Comment model tests
  - [x] Post service tests
  - [x] Feed service tests
- [x] Write unit tests for `groups` domain
  - [x] Group model tests
  - [x] Membership model tests
  - [x] Group service tests
- [x] Write unit tests for `notifications` domain
  - [x] Notification model tests
  - [x] Notification service tests
- [x] Write unit tests for `courses` domain
  - [x] Course model tests
  - [x] Year model tests
  - [x] Unit model tests
- [x] Write integration tests
  - [x] User registration flow
  - [x] Post creation and engagement flow
  - [x] Group creation and membership flow
  - [x] Follow/unfollow flow
  - [x] API endpoint tests
- [ ] Set up CI/CD for automated testing

**Implementation Notes:**
- Aim for 80% code coverage minimum
- Use factory_boy for test data generation
- Mock external services (email, SMS)
- Test database migrations

**Status:** ✅ COMPLETE - Test framework set up, unit tests for all domains, integration tests created. CI/CD pending.

---

### 1.3 API Completion
- [x] Create DRF serializers for all models
  - [x] User serializers
  - [x] Post serializers (already existed)
  - [x] Group serializers (already existed)
  - [x] Membership serializers (already existed)
  - [x] Notification serializers
  - [x] Course/Year/Unit serializers
- [x] Add comprehensive API viewsets
  - [x] Complete PostViewSet (already existed)
  - [x] Complete CommentViewSet (already existed)
  - [x] Complete GroupViewSet (already existed)
  - [x] Complete UserViewSet
  - [x] Complete NotificationViewSet
  - [x] Complete CourseViewSet
  - [x] Complete FollowViewSet
  - [x] Complete DeviceAccountViewSet
- [x] Add API pagination
- [x] Add API filtering and search
- [x] Add API versioning
- [x] Add OpenAPI/Swagger documentation
  - [x] Install drf-spectacular or drf-yasg
  - [x] Document all endpoints
  - [x] Add request/response examples
- [x] Add API rate limiting
- [x] Add API authentication (JWT or token-based)

**Implementation Notes:**
- Follow REST best practices
- Use ViewSets for consistency
- Add proper error handling
- Document authentication requirements

**Status:** ✅ COMPLETE - All ViewSets completed, serializers created, pagination/filtering/search/versioning/docs/rate limiting/JWT all configured.

---

## Phase 2: Real-time & Communication Features

### 2.1 Real-time Notifications
- [ ] Set up Django Channels
  - [ ] Install channels and channels_redis
  - [ ] Configure ASGI application
  - [ ] Set up Redis as channel layer
- [ ] Create WebSocket consumers
  - [ ] Notification consumer
  - [ ] Feed update consumer
  - [ ] Online status consumer
- [ ] Implement real-time notification delivery
- [ ] Add online status indicators
  - [ ] Track user online/offline status
  - [ ] Display online status on profiles
  - [ ] Show online users in groups
- [ ] Add typing indicators for messaging
- [ ] Test WebSocket connections
- [ ] Handle connection failures gracefully

**Implementation Notes:**
- Use Redis for channel layer in production
- Implement reconnection logic
- Add heartbeat for connection health
- Scale with multiple channel workers

---

### 2.2 Messaging System
- [ ] Create Message model
  - [ ] sender (ForeignKey to User)
  - [ ] recipient (ForeignKey to User, nullable)
  - [ ] group (ForeignKey to Group, nullable)
  - [ ] content (TextField)
  - [ ] created_at (DateTimeField)
  - [ ] read_at (DateTimeField, nullable)
  - [ ] attachments (FileField, nullable)
- [ ] Create Conversation model (for DMs)
  - [ ] participants (ManyToMany to User)
  - [ ] created_at
  - [ ] updated_at
- [ ] Create messaging views
  - [ ] Message list view
  - [ ] Conversation list view
  - [ ] Send message view
  - [ ] Mark as read view
- [ ] Create messaging API endpoints
  - [ ] GET/POST /api/messages/
  - [ ] GET /api/conversations/
  - [ ] POST /api/conversations/
  - [ ] GET /api/conversations/{id}/messages/
- [ ] Implement real-time messaging via WebSocket
- [ ] Add message search
- [ ] Add message forwarding
- [ ] Add message deletion (with undo option)
- [ ] Add message reactions
- [ ] Add typing indicators
- [ ] Add message read receipts

**Implementation Notes:**
- Support both DMs and group messages
- Use WebSocket for real-time delivery
- Implement message encryption for security
- Add message pagination for large conversations

---

## Phase 3: Enhanced Content Features

### 3.1 Post Management
- [ ] Add post editing functionality
  - [ ] Edit view with form
  - [ ] API endpoint for editing
  - [ ] Show edit history
  - [ ] Track who edited and when
- [ ] Add post scheduling
  - [ ] Schedule datetime field
  - [ ] Background task to publish scheduled posts
  - [ ] UI for scheduling
- [ ] Add draft posts
  - [ ] is_draft field
  - [ ] Draft management view
  - [ ] Auto-save drafts
- [ ] Add post bookmarking/saving
  - [ ] SavedPost model
  - [ ] Save/unsave functionality
  - [ ] Saved posts view
  - [ ] Organize into collections
- [ ] Add rich text editor
  - [ ] Integrate Quill or TinyMCE
  - [ ] Support formatting (bold, italic, headers)
  - [ ] Support links and mentions
  - [ ] Sanitize HTML output
- [ ] Add hashtag system
  - [ ] Extract hashtags from content
  - [ ] Hashtag model
  - [ ] Hashtag pages
  - [ ] Trending hashtags
- [ ] Add mention/tagging system
  - [ ] Parse @username in content
  - [ ] Notify mentioned users
  - [ ] Show mentions in notifications
- [ ] Add poll posts
  - [ ] Poll model with options
  - [ ] Vote tracking
  - [ ] Poll results view
- [ ] Add event posts
  - [ ] Event model with date/time
  - [ ] RSVP functionality
  - [ ] Calendar integration

**Implementation Notes:**
- Use Celery for scheduled posts
- Implement version control for edits
- Add content moderation for rich text
- Optimize hashtag queries with indexing

---

### 3.2 File & Document Management
- [ ] Add file versioning
  - [ ] DocumentVersion model
  - [ ] Version history view
  - [ ] Restore previous versions
  - [ ] Compare versions
- [ ] Add document preview
  - [ ] PDF preview
  - [ ] Image preview
  - [ ] Video preview
  - [ ] Document thumbnails
- [ ] Add file organization
  - [ ] Folder model
  - [ ] Folder hierarchy
  - [ ] Drag-and-drop organization
  - [ ] Bulk operations
- [ ] Add download tracking
  - [ ] DownloadLog model
  - [ ] Download analytics
  - [ ] Download limits
- [ ] Add file sharing permissions
  - [ ] Public/private links
  - [ ] Expiration dates for shared links
  - [ ] Password-protected links
- [ ] Add file comments
  - [ ] Comment on documents
  - [ ] Inline annotations for images

**Implementation Notes:**
- Use cloud storage (S3, GCS) for scalability
- Implement CDN for file delivery
- Add virus scanning for uploads
- Compress images/videos automatically

---

## Phase 4: User Experience Improvements

### 4.1 Search & Discovery
- [ ] Enhance search functionality
  - [ ] Full-text search with Elasticsearch
  - [ ] Search suggestions/autocomplete
  - [ ] Search history
  - [ ] Advanced search syntax
  - [ ] Search across posts, users, groups, units
- [ ] Add advanced filters
  - [ ] Filter by date range
  - [ ] Filter by popularity
  - [ ] Filter by content type
  - [ ] Filter by author
  - [ ] Save filter presets
- [ ] Add trending content
  - [ ] Trending posts algorithm
  - [ ] Trending topics
  - [ ] Trending groups
  - [ ] Trending users
- [ ] Add recommended content
  - [ ] Recommendation algorithm
  - [ ] "For You" feed
  - [ ] Similar posts
  - [ ] Suggested users to follow
  - [ ] Suggested groups to join

**Implementation Notes:**
- Use Elasticsearch for search
- Implement machine learning for recommendations
- Cache trending results
- A/B test recommendation algorithms

---

### 4.2 UI/UX Enhancements
- [ ] Add dark mode
  - [ ] CSS variables for theming
  - [ ] Toggle switch in settings
  - [ ] System preference detection
  - [ ] Persist user preference
- [ ] Improve accessibility
  - [ ] Add ARIA labels
  - [ ] Keyboard navigation
  - [ ] Screen reader support
  - [ ] High contrast mode
  - [ ] Font size controls
- [ ] Add skeleton loading states
- [ ] Add infinite scroll for feeds
- [ ] Add pull-to-refresh
- [ ] Add swipe gestures (mobile)
- [ ] Add haptic feedback (mobile)
- [ ] Improve error handling UI
- [ ] Add empty state illustrations

**Implementation Notes:**
- Follow WCAG 2.1 guidelines
- Test with screen readers
- Use CSS custom properties for theming
- Implement progressive enhancement

---

## Phase 5: Group Features Enhancement

### 5.1 Group Management
- [ ] Add group analytics
  - [ ] Member growth chart
  - [ ] Activity metrics
  - [ ] Engagement rates
  - [ ] Top contributors
  - [ ] Export analytics data
- [ ] Add group events
  - [ ] Event model
  - [ ] Event calendar
  - [ ] RSVP tracking
  - [ ] Event reminders
  - [ ] Recurring events
- [ ] Add group announcements
  - [ ] Pinned posts
  - [ ] Announcement banner
  - [ ] Announcement history
- [ ] Add group categories
  - [ ] Category model
  - [ ] Category browsing
  - [ ] Filter groups by category
- [ ] Enhance group search
  - [ ] Advanced filters
  - [ ] Sort by popularity/activity
  - [ ] Search within groups
- [ ] Add sub-groups
  - [ ] Parent/child group relationship
  - [ ] Inherited permissions
  - [ ] Sub-group discovery

**Implementation Notes:**
- Use Chart.js or D3 for analytics
- Implement calendar with fullcalendar.js
- Add ICS export for events
- Cache analytics calculations

---

## Phase 6: Notification Enhancements

### 6.1 Notification Management
- [ ] Add granular notification preferences
  - [ ] Per-type preferences
  - [ ] Per-group preferences
  - [ ] Per-user preferences
  - [ ] Quiet hours
  - [ ] Do not disturb mode
- [ ] Add notification scheduling
  - [ ] Quiet hours settings
  - [ ] Weekend preferences
  - [ ] Vacation mode
- [ ] Add push notifications
  - [ ] FCM integration
  - [ ] APNs integration
  - [ ] Push notification settings
  - [ ] Device management
- [ ] Enhance email notifications
  - [ ] Email templates
  - [ ] Digest emails (daily/weekly)
  - [ ] Email preferences per type
  - [ ] Unsubscribe links
- [ ] Add notification categories
  - [ ] Group notifications
  - [ ] Social notifications
  - [ ] System notifications
- [ ] Add notification sounds
  - [ ] Custom sounds per type
  - [] Sound settings

**Implementation Notes:**
- Use SendGrid or Mailgun for emails
- Implement email queue with Celery
- Test push notifications on both platforms
- Compress email digests

---

## Phase 7: Academic Features

### 7.1 Academic Tools
- [ ] Add assignment sharing
  - [ ] Assignment model
  - [ ] Due date tracking
  - [ ] Submission tracking
  - [ ] Grade display
- [ ] Add study groups
  - [ ] Study session scheduling
  - [ ] Session reminders
  - [ ] Attendance tracking
  - [ ] Notes sharing
- [ ] Add resource library
  - [ ] Resource model
  - [ ] Categorization
  - [ ] Rating system
  - [ ] Resource reviews
- [ ] Add grade tracking
  - [ ] Grade model
  - [ ] GPA calculation
  - [ ] Grade history
  - [ ] Grade trends
- [ ] Add class schedule integration
  - [ ] Schedule model
  - [ ] Calendar view
  - [ ] Conflict detection
  - [ ] Export to calendar apps
- [ ] Add lecture notes sharing
  - [ ] Note model
  - [ ] Rich text support
  - [ ] Collaboration features
  - [ ] Version control

**Implementation Notes:**
- Integrate with university systems if possible
- Add privacy controls for grades
- Implement FERPA compliance
- Use academic calendar standards

---

## Phase 8: Moderation & Safety

### 8.1 Content Moderation
- [ ] Add automated content filtering
  - [ ] Profanity filter
  - [ ] Spam detection
  - [ ] Link scanning
  - [ ] Image moderation (AI)
- [ ] Add user blocking
  - [ ] Block model
  - [ ] Block list view
  - [ ] Block functionality
  - [ ] Blocked users cannot interact
- [ ] Add report dashboard
  - [ ] Admin report queue
  - [ ] Report categorization
  - [ ] Bulk actions
  - [ ] Report analytics
- [ ] Add appeal system
  - [ ] Appeal model
  - [ ] Appeal submission form
  - [ ] Appeal review workflow
  - [ ] Appeal notifications
- [ ] Add user bans
  - [ ] Ban model with duration
  - [ ] Ban reasons
  - [ ] Ban history
  - [ ] Temporary vs permanent bans
- [ ] Add safety center
  - [ ] Safety resources
  - [ ] Reporting guides
  - [ ] Privacy settings hub

**Implementation Notes:**
- Use AI services for content moderation
- Implement escalation workflows
- Add audit logs for all moderation actions
- Provide transparency to users

---

## Phase 9: Analytics & Insights

### 9.1 User Analytics
- [ ] Add user engagement analytics
  - [ ] Post engagement metrics
  - [ ] Follower growth
  - [ ] Profile views
  - [ ] Activity heatmaps
- [ ] Add content analytics
  - [ ] Post performance
  - [ ] Reach metrics
  - [ ] Demographic data
  - [ ] Best posting times
- [ ] Add admin dashboard
  - [ ] Site-wide metrics
  - [ ] User statistics
  - [ ] Content statistics
  - [ ] System health
- [ ] Add activity logs
  - [ ] Log all admin actions
  - [ ] Log sensitive operations
  - [ ] Log retention policy
  - [ ] Log export functionality
- [ ] Add export features
  - [ ] Export user data
  - [ ] Export group data
  - [ ] GDPR compliance

**Implementation Notes:**
- Use analytics database (separate from main DB)
- Implement data aggregation jobs
- Add real-time dashboard updates
- Comply with data privacy regulations

---

## Phase 10: Performance & Scalability

### 10.1 Caching & Optimization
- [ ] Implement Redis caching
  - [ ] Cache frequently accessed data
  - [ ] Cache query results
  - [ ] Cache rendered templates
  - [ ] Cache API responses
- [ ] Implement Celery background tasks
  - [ ] Email sending
  - [ ] Image processing
  - [ ] Scheduled posts
  - [ ] Analytics aggregation
- [ ] Database optimization
  - [ ] Add missing indexes
  - [ ] Optimize slow queries
  - [ ] Implement query caching
  - [ ] Add database read replicas
- [ ] Add CDN integration
  - [ ] Serve static files via CDN
  - [ ] Serve media files via CDN
  - [ ] Configure cache headers
- [ ] Enhance image optimization
  - [ ] WebP format support
  - [ ] Responsive images
  - [ ] Lazy loading
  - [ ] Progressive loading

**Implementation Notes:**
- Monitor cache hit rates
- Use Redis clustering for scalability
- Implement cache invalidation strategy
- Set up database monitoring

---

## Phase 11: Security Enhancements

### 11.1 Authentication & Authorization
- [ ] Add two-factor authentication (2FA)
  - [ ] TOTP support (Google Authenticator)
  - [ ] SMS 2FA
  - [ ] Backup codes
  - [ ] 2FA settings
- [ ] Enhance session management
  - [ ] Session timeout controls
  - [ ] Session revocation
  - [ ] Active sessions view
  - [ ] Login history
- [ ] Add API rate limiting
  - [ ] Per-user limits
  - [ ] Per-endpoint limits
  - [ ] Burst allowance
  - [ ] Rate limit headers
- [ ] Configure CORS
  - [ ] Allow specific origins
  - [ ] Credentials support
  - [ ] Preflight handling
- [ ] Add security headers
  - [ ] Content Security Policy (CSP)
  - [ ] HTTP Strict Transport Security (HSTS)
  - [ ] X-Frame-Options
  - [ ] X-Content-Type-Options
- [ ] Add password policies
  - [ ] Minimum length
  - [ ] Complexity requirements
  - [ ] Password history
  - [ ] Expiration

**Implementation Notes:**
- Use django-axes for rate limiting
- Implement password hashing with Argon2
- Add security audit logging
- Regular security scans

---

## Phase 12: Mobile Experience

### 12.1 Mobile Optimization
- [ ] Convert to Progressive Web App (PWA)
  - [ ] Add service worker
  - [ ] Add manifest.json
  - [ ] Offline support
  - [ ] Install prompt
- [ ] Develop native mobile apps
  - [ ] iOS app (React Native or Swift)
  - [ ] Android app (React Native or Kotlin)
  - [ ] Push notifications
  - [ ] Biometric authentication
- [ ] Responsive design audit
  - [ ] Test on various devices
  - [ ] Fix layout issues
  - [ ] Touch-friendly targets
  - [ ] Mobile navigation

**Implementation Notes:**
- Use workbox for service workers
- Implement offline data sync
- Test on real devices
- Consider cross-platform frameworks

---

## Phase 13: Integration Features

### 13.1 Third-Party Integrations
- [ ] Calendar integration
  - [ ] Google Calendar sync
  - [ ] Outlook Calendar sync
  - [ ] iCal export/import
- [ ] File storage integration
  - [ ] Google Drive integration
  - [ ] Dropbox integration
  - [ ] OneDrive integration
- [ ] Social media sharing
  - [ ] Share to Twitter
  - [ ] Share to Facebook
  - [ ] Share to LinkedIn
  - [ ] Share to WhatsApp
- [ ] SSO integration
  - [ ] Google OAuth
  - [ ] Microsoft OAuth
  - [ ] GitHub OAuth
- [ ] Video integration
  - [ ] YouTube embeds
  - [ ] Vimeo embeds
  - [ ] Video conferencing links

**Implementation Notes:**
- Use OAuth 2.0 for authentication
- Handle API rate limits
- Provide clear error messages
- Allow users to revoke access

---

## Implementation Guidelines

### General Principles
1. **One feature at a time** - Complete each checkbox before moving to the next
2. **Test thoroughly** - Write tests before implementing features
3. **Document changes** - Update relevant documentation after each feature
4. **Code review** - Review code changes before merging
5. **Monitor performance** - Check impact on site performance after each feature

### Feature Selection Criteria
- **User value** - Does this benefit users?
- **Technical feasibility** - Can this be implemented reliably?
- **Resource requirements** - Do we have the time and expertise?
- **Dependencies** - Are there prerequisite features?

### Suggested Implementation Order
1. Start with **Phase 1** (Critical Technical Debt)
2. Move to **Phase 2** (Real-time & Communication)
3. Implement **Phase 3** (Enhanced Content Features)
4. Add **Phase 4** (User Experience Improvements)
5. Continue with remaining phases based on priority

### Tracking Progress
- Mark items as [x] when completed
- Mark items as [~] when in progress
- Add notes for any blockers or issues
- Update this document regularly

---

## Notes

### Custom Notes
- Add any custom notes or decisions here
- Track any deviations from the plan
- Document any architectural decisions

### Blocked Items
- List any features that are blocked and why
- Note when they might become unblocked

### Deferred Items
- List features intentionally deferred
- Note when they might be revisited
