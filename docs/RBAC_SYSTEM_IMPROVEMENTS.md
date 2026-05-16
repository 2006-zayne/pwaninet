# Role-Based Access Control (RBAC) System Improvements

## Overview

This document explains the comprehensive RBAC system implemented for the Django social network, providing strict separation between global roles and group-level permissions with a scalable, maintainable architecture.

---

## 1. Model Changes

### User Model (`users/models.py`)

**Added:**
- `global_role` field with choices: PRESIDENT, DELEGATE, VERIFIED, NORMAL
- Global roles are for identity and badges ONLY - they do NOT grant automatic permissions in groups

**Purpose:**
- Distinguish user identity levels (e.g., student government, delegates)
- Display badges on profiles
- No permission logic tied to global roles

---

### Group Model (`groups/models.py`)

**Renamed:** `Groups` → `Group` (singular for consistency)

**Added:**
- `course` (ForeignKey, nullable) - Links to Course model
- `year` (ForeignKey, nullable) - Links to Year model
- `created_at` (DateTimeField, auto_now_add=True) - Timestamp for group creation

**Removed:**
- `members` (ManyToManyField) - Replaced by Membership model

**Purpose:**
- Support official academic groups tied to specific courses/years
- Enable course/year-based access restrictions
- Proper timestamp tracking
- Cleaner relationship management through Membership model

---

### Membership Model (`groups/models.py`)

**New Model:**

```python
class Membership(models.Model):
    user = ForeignKey(User)
    group = ForeignKey(Group)
    role = CharField(choices=[ADMIN, MODERATOR, DELEGATE, MEMBER])
    status = CharField(choices=[PENDING, APPROVED, REJECTED])
    joined_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'group')
```

**Roles:**
- **ADMIN** - Full group management (max 5 per group)
- **MODERATOR** - Delete posts, moderate users
- **DELEGATE** - Limited moderation (report escalation)
- **MEMBER** - Create posts, comment, report, leave group

**Status:**
- **PENDING** - Join request awaiting approval
- **APPROVED** - Active member with permissions
- **REJECTED** - Join request denied

**Purpose:**
- Explicit membership tracking with approval workflow
- Role-based permissions within groups
- Audit trail (joined_at)
- Prevents duplicate memberships

---

### Post Model (`posts/models.py`)

**Changed:**
- `date` → `created_at` (consistent naming)
- Added `updated_at` (DateTimeField, auto_now=True)
- Updated ForeignKey to reference `Group` (not `Groups`)

**Purpose:**
- Clear field naming conventions
- Track when posts are modified
- Consistent with new Group model

---

### Report Model (`posts/models.py`)

**New Model:**

```python
class Report(models.Model):
    reporter = ForeignKey(User)
    post = ForeignKey(Post)
    reason = TextField()
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('reporter', 'post')
```

**Purpose:**
- Content moderation system
- Prevent duplicate reports per user
- Track who reported what and when

---

## 2. Permission System (`groups/permissions.py`)

### Custom Permission Classes

#### `IsApprovedMember`
- Only approved members can interact in groups
- Checks membership status = APPROVED
- Used for group-level actions

#### `IsGroupAdmin`
- Checks if user has ADMIN role in the group
- Used for admin-only operations

#### `IsGroupModerator`
- Checks if user is MODERATOR or ADMIN
- Used for post deletion, user moderation

#### `IsGroupDelegate`
- Checks if user is DELEGATE, MODERATOR, or ADMIN
- Used for limited moderation tasks

#### `CanManageGroup`
- Edit group details or delete group
- Group creator is always an admin
- Only admins can perform these actions

#### `CanManageMembership`
- Approve/reject join requests
- Assign roles to members
- **Enforces max 5 admins per group constraint**
- Prevents self-demotion from admin

#### `CanDeletePost`
- Author OR admin can delete post
- Author can delete their own posts
- Group admins can delete any post in their group

#### `CanEditPost`
- Only author can edit their post
- Strict ownership control

#### `CanJoinOfficialGroup`
- Only users with matching course AND year can join official groups
- Others can view but cannot join or post
- Enforces academic group restrictions

#### `IsPostAuthorOrReadOnly`
- Read access for approved members
- Write access only for author
- Used for post viewsets

---

## 3. API Endpoints

### Group Endpoints (`groups/views.py`)

#### `POST /groups/api/{id}/join/`
- Request to join a group
- Checks official group restrictions (course + year)
- Creates PENDING membership
- Returns membership details

#### `POST /groups/api/{id}/approve/{user_id}/`
- Approve a join request (admin only)
- Updates membership status to APPROVED
- Returns updated membership

#### `POST /groups/api/{id}/reject/{user_id}/`
- Reject a join request (admin only)
- Updates membership status to REJECTED
- Returns updated membership

#### `POST /groups/api/{id}/assign-role/`
- Assign a role to a member (admin only)
- **Enforces max 5 admins per group**
- Prevents self-demotion from admin
- Returns updated membership

#### `GET /groups/api/{id}/members/`
- List all members of a group
- Returns approved members only
- Includes role and status information

#### `POST /groups/api/{id}/leave/`
- Leave a group
- Prevents leaving as last admin
- Deletes membership

#### Full CRUD for Groups
- Create, Read, Update, Delete groups
- Update/delete restricted to admins
- Creator automatically becomes admin

---

### Post Endpoints (`posts/views.py`)

#### `POST /posts/api/posts/create/`
- Create a new post
- Only approved members can post in groups
- Author automatically assigned

#### `PUT /posts/api/posts/{id}/edit/`
- Edit a post (author only)
- CanEditPost permission enforced

#### `DELETE /posts/api/posts/{id}/delete/`
- Delete a post (author or admin)
- CanDeletePost permission enforced

#### `POST /posts/api/posts/{id}/report/`
- Report a post
- Any user can report
- Prevents duplicate reports per user

#### `POST /posts/api/posts/{id}/like/`
- Like/unlike a post
- Must be approved member to like group posts

#### `GET /posts/api/posts/{id}/comments/`
- List all comments for a post

#### Full CRUD for Comments
- Create, Read, Update, Delete comments
- Membership checks enforced

#### Report ViewSet
- Read-only for admins
- Only shows reports for posts in admin's groups

---

## 4. Core Rules & Constraints

### Membership Workflow
1. User requests to join group → PENDING status
2. Admin approves → APPROVED status (grants permissions)
3. Admin rejects → REJECTED status (no access)
4. User can leave at any time (unless last admin)

### Official Group Restrictions
- Only users with matching **course AND year** can join
- Others can view but cannot join or post
- Automatically enforced in join logic

### Admin Constraints
- **Maximum 5 admins per group** (including creator)
- Cannot demote yourself from admin
- Must assign another admin before leaving

### Post Rules
- Only APPROVED members can create posts
- Only author can edit their post
- Author OR admin can delete post
- Any user can report post
- Any user can hide posts (frontend/local only)

---

## 5. Strict Separation of Concerns

### Global Roles vs Group Permissions
- **Global roles** (PRESIDENT, DELEGATE, VERIFIED, NORMAL) are for identity/badges ONLY
- They do NOT grant automatic permissions in groups
- Group permissions are determined solely by Membership.role
- This prevents privilege escalation and maintains clean RBAC

### Badge System
- Badges display based on:
  - `global_role` (e.g., President badge)
  - `group_membership.role` (e.g., Admin badge)
- Viewer does NOT see their own badges
- Other users can see badges on profiles

---

## 6. Database Migration Requirements

After implementing these changes, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

**Note:** The migration will:
- Rename Groups table to Group
- Add global_role to User
- Add course, year, created_at to Group
- Remove members M2M from Group
- Create Membership table
- Add updated_at to Post
- Create Report table

---

## 7. Code Updates Required

All files referencing `Groups` have been updated to `Group`:
- `core/admin.py`
- `core/management/commands/seed_social.py`
- `core/signals.py`
- `core/forms.py`
- `core/views.py`
- `groups/queries/group_queries.py`
- `notifications/signals.py`
- `notifications/models.py`
- `posts/services/post_service.py`
- `posts/queries/search_queries.py`
- `posts/queries/feed_queries.py`

Membership logic updated in queries to use the new Membership model instead of direct M2M relationships.

---

## 8. Architecture Benefits

### Scalability
- Modular permission classes - easy to extend
- Clear separation of concerns
- Reusable components across the system

### Maintainability
- Explicit models for each concept
- Clear naming conventions
- Well-documented permission logic
- Consistent patterns throughout

### Security
- Strict permission checks at multiple layers
- No automatic privilege escalation
- Enforced constraints (max admins, course/year matching)
- Audit trail with timestamps

### Flexibility
- Easy to add new roles
- Easy to modify permission logic
- Membership status workflow can be extended
- Badge system is decoupled from permissions

---

## 9. Testing Recommendations

### Unit Tests
- Test each permission class independently
- Test role assignment constraints
- Test official group restrictions
- Test membership workflow (pending → approved)

### Integration Tests
- Test full join workflow
- Test post creation with different roles
- Test admin assignment with max constraint
- Test official group join rejection

### Edge Cases
- Last admin attempting to leave
- Self-demotion from admin
- Duplicate membership requests
- Duplicate reports on same post

---

## 10. Future Enhancements

### Potential Additions
- Role expiration (temporary admin assignments)
- Membership invitation system
- Group bans (separate from rejection)
- Audit logging for admin actions
- Role hierarchy customization
- Group-specific permission overrides

### Badge Extensions
- Achievement badges (e.g., "Top Contributor")
- Event-based badges (e.g., "Event Organizer")
- Time-based badges (e.g., "Early Adopter")

---

## Summary

This RBAC system provides:
- ✅ Clean separation between global identity and group permissions
- ✅ Explicit membership tracking with approval workflow
- ✅ Role-based permissions with clear hierarchy
- ✅ Official group restrictions (course + year matching)
- ✅ Enforced constraints (max 5 admins per group)
- ✅ Scalable, maintainable architecture
- ✅ Comprehensive API endpoints
- ✅ Custom permission classes for fine-grained control
- ✅ Badge system decoupled from permissions

The system is production-ready, secure, and designed for easy extension as requirements evolve.
