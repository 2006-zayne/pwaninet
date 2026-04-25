# Pwaninet Features Documentation

## Overview
Pwaninet is a university social network built with Django, designed for students at Pwani University. It provides a platform for social interaction, academic collaboration, and community building.

---

## Current Features

### 1. User Management

#### User Registration & Authentication
- **Registration**: Users can register with username, password, and profile information
- **Login/Logout**: Django authentication system with custom login/logout views
- **Profile Completion**: Users can complete their profile with course, year, and bio information
- **Profile Pictures**: Users can upload profile pictures with automatic image compression (max 1080x1080, JPEG format)

#### User Roles
- **Global Roles**: 
  - President - Highest level authority
  - Delegate - Representative role
  - Verified - Verified user badge
  - Normal - Standard user
- **Profile Fields**:
  - First name, second name, last name
  - Course and year (academic information)
  - Bio (500 characters max)
  - Profile picture

#### Follow System
- **Follow/Unfollow**: Users can follow other users
- **Followers/Following Counts**: Displayed on user profiles
- **Follow Suggestions**: Algorithm suggests users to follow based on group memberships

---

### 2. Posts & Content

#### Post Creation
- **Text Posts**: Users can create text-based posts
- **Media Posts**: Support for images, videos, and documents
- **Post Styling**: Gradient background options (Ocean Blue, Forest Green, Magma Red, Midnight Purple, Desert Storm, Night Ops)
- **Contextual Posts**: Posts can be associated with:
  - Groups
  - Courses
  - Academic units

#### Post Engagement
- **Likes**: Users can like/unlike posts
- **Comments**: Users can comment on posts
- **Comment Likes**: Users can like comments
- **Post Likers List**: View all users who liked a post
- **Reports**: Users can report inappropriate posts with reasons

#### Feed System
- **Ranked Feed**: Posts ranked by engagement score (likes + 2*comments)
- **Cursor-Based Pagination**: Scalable infinite scroll without offset performance issues
- **Personalized Feed**: Shows posts from:
  - Followed users
  - Groups the user is a member of
  - Same course and year peers
- **Unit-Specific Feeds**: View posts filtered by academic unit

#### Search
- **Post Search**: Search across posts by content
- **User Search**: Search for users by username

---

### 3. Groups

#### Group Management
- **Create Groups**: Users can create groups with name, description, and profile picture
- **Official Groups**: Groups can be marked as official (university-sponsored)
- **Group Context**: Groups can be associated with specific courses and years

#### Membership System
- **Membership Roles**:
  - Admin - Full control over group
  - Moderator - Can moderate content
  - Delegate - Representative role
  - Member - Standard member
- **Membership Status**:
  - Pending - Awaiting approval
  - Approved - Active member
  - Rejected - Membership denied
- **Join/Leave**: Users can request to join or leave groups
- **Invitations**: Admins can invite users to groups
- **Invite Responses**: Users can accept or decline group invitations

#### Group Content
- **Group Posts**: Posts can be created within groups
- **Group Dashboard**: View all user's groups and discover new ones
- **Suggested Groups**: Algorithm suggests groups based on following relationships

---

### 4. Notifications

#### Notification Types
- **Group Invites**: Notifications for group membership invitations
- **General Alerts**: System-wide announcements
- **Post Likes**: Notifications when users like your posts
- **New Followers**: Notifications when users follow you
- **Group Requests**: Notifications for group join requests (for admins)
- **Group Approvals**: Notifications when group membership is approved

#### Notification Features
- **Unread Count**: Cached unread notification count (30-second cache)
- **Mark as Read**: Individual or bulk mark as read functionality
- **Real-time Updates**: Notification count updates in real-time
- **Context Links**: Notifications link to relevant content (posts, groups, profiles)

---

### 5. Academic Structure

#### Course Management
- **Courses**: Academic programs (e.g., Computer Science, Business)
- **Years**: Academic years within courses (Year 1, Year 2, etc.)
- **Units**: Specific subjects/units within course years
- **Hierarchical Structure**: Course → Years → Units

#### Academic Integration
- **User-Course Association**: Users belong to specific courses and years
- **Unit-Specific Content**: Posts can be tagged with academic units
- **Peer Discovery**: Feed shows posts from same course/year peers

---

### 6. Technical Features

#### Architecture
- **Domain-Driven Design**: Separated into domain apps (users, posts, groups, notifications, courses)
- **Service Layer**: Business logic separated into service modules
- **Query Layer**: Database queries separated into query modules
- **Environment-Based Settings**: Separate configurations for local and production

#### Performance
- **Database Indexing**: Indexed fields for efficient queries (created_at, foreign keys)
- **Query Optimization**: 
  - select_related for foreign keys
  - prefetch_related for many-to-many relationships
  - Cursor-based pagination for feeds
- **Caching**: Redis caching for notification counts
- **Image Compression**: Automatic image optimization on upload

#### Background Tasks
- **Celery Integration**: Configured for asynchronous task processing
- **Celery Beat**: Scheduled task support

#### Database
- **Development**: SQLite for local development
- **Production**: PostgreSQL configured for production deployment

#### Deployment
- **Docker Support**: Docker and Docker Compose configuration
- **Static Files**: WhiteNoise for static file serving
- **Media Files**: Configured media file handling

---

## Possible Modifications & Improvements

### High Priority

#### 1. Complete Domain Migration
**Status**: In Progress
**Description**: Move remaining views and forms from core app to domain apps
**Benefits**:
- Better code organization
- Easier maintenance
- Clearer domain boundaries
**Steps**:
- Migrate views from core to respective domain apps
- Migrate forms from core to respective domain apps
- Update URL references
- Remove core app after complete migration

#### 2. Add API Layer
**Description**: Implement REST API endpoints using Django REST Framework
**Benefits**:
- Enable mobile app development
- Third-party integrations
- Better separation of concerns
**Endpoints to Add**:
- User authentication (JWT)
- CRUD operations for posts, comments, likes
- Group management APIs
- Notification APIs

#### 3. Enhanced Feed Algorithm
**Current**: Simple score-based ranking (likes + 2*comments)
**Proposed Improvements**:
- **Time Decay**: Older posts get lower scores over time
- **Relationship Boost**: Weight posts from same group/course higher
- **Personalization**: Machine learning-based personalization
- **Re-ranking**: Real-time re-ranking on new posts
- **Content Analysis**: Analyze post content for relevance

#### 4. Real-time Features
**Description**: Add real-time updates using WebSockets
**Features**:
- Real-time feed updates
- Live notification delivery
- Online status indicators
- Real-time commenting
- Typing indicators

---

### Medium Priority

#### 5. Enhanced Group Features
**Proposed Additions**:
- **Group Events**: Create and manage group events
- **Group Announcements**: Pinned posts for important announcements
- **Group Polls**: Create polls within groups
- **File Sharing**: Shared file repositories for groups
- **Group Analytics**: Engagement metrics for group admins

#### 6. Advanced User Features
**Proposed Additions**:
- **User Blocking**: Block unwanted users
- **Privacy Settings**: Control profile visibility and post audience
- **User Stories**: Ephemeral content (24-hour stories)
- **Saved Posts**: Bookmark posts for later
- **Post Drafts**: Save posts as drafts before publishing

#### 7. Enhanced Search
**Current**: Basic text search
**Proposed Improvements**:
- **Full-text Search**: PostgreSQL full-text search or Elasticsearch
- **Filters**: Filter by date, engagement, author, etc.
- **Autocomplete**: Real-time search suggestions
- **Advanced Query**: Boolean operators, phrase search
- **Search History**: User's recent searches

#### 8. Messaging System
**Description**: Direct messaging between users
**Features**:
- One-on-one messaging
- Group messaging
- Message reactions
- File sharing in messages
- Read receipts
- Message search

---

### Low Priority

#### 9. Gamification
**Proposed Features**:
- **User Badges**: Achievement badges for various activities
- **Leaderboards**: Top contributors, most liked posts, etc.
- **Points System**: Earn points for engagement
- **Streaks**: Daily engagement streaks

#### 10. Content Moderation
**Proposed Features**:
- **Automated Moderation**: AI-based content filtering
- **Report Management**: Admin dashboard for handling reports
- **Content Flags**: Flag suspicious content for review
- **User Warnings**: Warning system for policy violations

#### 11. Analytics Dashboard
**Proposed Features**:
- **User Analytics**: Profile views, engagement metrics
- **Post Analytics**: Reach, engagement over time
- **Group Analytics**: Member growth, activity levels
- **Admin Analytics**: Platform-wide statistics

#### 12. Mobile Optimization
**Proposed Improvements**:
- **Progressive Web App (PWA)**: Installable web app
- **Offline Support**: Cache content for offline viewing
- **Push Notifications**: Browser push notifications
- **Mobile-First Design**: Enhanced mobile experience

---

### Technical Improvements

#### 13. Testing
**Current**: No test suite
**Proposed**:
- Unit tests for all services
- Integration tests for views
- End-to-end tests with Playwright/Selenium
- Test coverage reporting

#### 14. Monitoring & Logging
**Proposed**:
- **Error Tracking**: Sentry integration
- **Performance Monitoring**: New Relic or similar
- **Application Logging**: Structured logging with log levels
- **Health Checks**: Endpoint for monitoring service health

#### 15. Security Enhancements
**Proposed**:
- **Rate Limiting**: Prevent API abuse
- **CSRF Protection**: Already implemented, verify coverage
- **XSS Protection**: Content sanitization
- **SQL Injection Prevention**: Use ORM properly (already done)
- **Security Headers**: Implement security headers (CSP, HSTS)

#### 16. Database Optimization
**Proposed**:
- **Connection Pooling**: PgBouncer for PostgreSQL
- **Read Replicas**: Separate read replicas for scaling
- **Query Analysis**: Slow query logging and optimization
- **Database Partitioning**: Partition large tables by date

#### 17. CDN Integration
**Proposed**:
- **Static Files CDN**: Serve static files via CDN
- **Media Files CDN**: Serve user uploads via CDN
- **Image Optimization**: CDN-based image optimization

---

## Migration Status

### Completed
- ✅ Domain app structure created
- ✅ Models moved to domain apps
- ✅ Services moved to domain apps
- ✅ Queries moved to domain apps
- ✅ URLs reorganized by domain
- ✅ Environment-based settings implemented
- ✅ PostgreSQL and Redis configured
- ✅ Django REST Framework added
- ✅ Celery configured
- ✅ Docker setup completed
- ✅ Feed ranking system with cursor-based pagination

### In Progress
- ⏳ Moving views from core to domain apps
- ⏳ Moving forms from core to domain apps

### Pending
- ⏳ Remove core app after complete migration
- ⏳ Add admin.py for each domain app
- ⏳ Create DRF serializers and viewsets for APIs
- ⏳ Add tests for domain apps
- ⏳ Implement real-time features
- ⏳ Add messaging system

---

## Next Steps

1. **Complete Domain Migration**: Finish moving views and forms to domain apps
2. **Add Testing**: Implement comprehensive test suite
3. **API Development**: Create REST API endpoints
4. **Real-time Features**: Implement WebSocket-based features
5. **Enhanced Search**: Add full-text search capabilities
6. **Mobile Optimization**: Implement PWA features

---

## Conclusion

Pwaninet is a well-structured university social network with a solid foundation. The domain-driven architecture provides good separation of concerns, and the cursor-based feed system is scalable. The proposed improvements focus on completing the migration, adding real-time capabilities, and enhancing user experience with modern social features.
