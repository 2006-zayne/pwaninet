# Profile Switching Feature Implementation Plan

## Overview
Add a profile/account switching feature that allows users to easily switch between multiple accounts on the same device. This is useful for users managing multiple DMO accounts (e.g., testing different roles, managing multiple personas).

## Current State Analysis

### Authentication System
- **User Model**: Custom `users.User` model extending `AbstractUser`
- **Authentication**: Django session-based authentication (`SessionAuthentication`)
- **Session Storage**: Default Django session backend (database-backed)
- **Login/Logout**: Uses Django's built-in `LoginView` and `LogoutView`
- **Profile URL**: `/user/<username>/` for viewing profiles
- **Profile Edit**: `/profile/edit/` for updating profile

### Current Limitations
- No mechanism to track multiple accounts on the same device
- No quick switch functionality between accounts
- Users must manually log out and log in again to switch accounts

## Proposed Solution

### 1. Database Model Changes

#### New Model: `DeviceAccount`
Create a new model to track accounts used on a device:

```python
class DeviceAccount(models.Model):
    """Tracks accounts that have been used on a specific device"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_accounts')
    device_id = models.CharField(max_length=255, db_index=True)  # Browser/device fingerprint
    last_used = models.DateTimeField(auto_now=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)  # Store session key for quick switch
    
    class Meta:
        unique_together = ('user', 'device_id')
        ordering = ['-last_used']
```

**Migration Required**: Yes

### 2. Backend Changes

#### A. Device Identification Service
Create a service to generate and manage device identifiers:
- **File**: `users/services/device_service.py`
- Generate device ID using browser fingerprint (user agent + localStorage)
- Store device ID in browser localStorage
- Provide helper functions to get/set device ID

#### B. Profile Switching Views
Add new views in `users/views.py`:

1. **`switch_account_view`** - Switch to a different account
   - Accepts `user_id` as parameter
   - Validates the account is associated with the device
   - Logs out current user and logs in the target user
   - Updates `last_used` timestamp
   - Redirects to home or profile

2. **`get_device_accounts_view`** - Get list of accounts for current device
   - Returns JSON list of accounts associated with device
   - Includes user info (username, profile_pic, last_used)
   - Used for the account switcher dropdown

3. **`remove_account_from_device_view`** - Remove account from device list
   - Allows users to remove an account from the device's account list
   - Does not delete the user account, just removes the device association

#### C. URL Configuration
Add new URLs in `users/urls.py`:
```python
path('accounts/switch/<int:user_id>/', views.switch_account_view, name='switch_account'),
path('accounts/device-accounts/', views.get_device_accounts_view, name='device_accounts'),
path('accounts/remove/<int:user_id>/', views.remove_account_from_device_view, name='remove_account_from_device'),
```

#### D. Signal Handler
Add a signal handler to automatically create/update `DeviceAccount` when a user logs in:
- **File**: `users/signals.py` (or update existing)
- Listen for `user_logged_in` signal
- Create or update `DeviceAccount` record with current device ID

### 3. Frontend Changes

#### A. JavaScript Device ID Management
Create a JS file to manage device identification:
- **File**: `static/js/device_manager.js`
- Generate device ID on first visit
- Store in localStorage
- Include in base template

#### B. Profile Section UI Updates
Update profile templates to include account switcher:

1. **Profile Header Dropdown**
   - Add a dropdown button near the profile picture
   - Shows "Switch Account" option
   - Opens modal with list of available accounts

2. **Account Switcher Modal**
   - **Template**: `users/templates/users/partials/account_switcher_modal.html`
   - List all accounts associated with the device
   - Show profile picture, username, last used time
   - "Switch" button for each account
   - "Remove" button to remove account from device list
   - "Add Account" button to log in with new account

3. **Account List Item Template**
   - **Template**: `users/templates/users/partials/account_list_item.html`
   - Reusable component for displaying account in the list
   - Use HTMX for dynamic loading

#### C. Base Template Updates
Update `core/templates/base.html`:
- Include `device_manager.js` script
- Add device ID to all AJAX requests via HTMX headers

### 4. Security Considerations

#### A. Session Validation
- Verify the target account is actually associated with the device before switching
- Require re-authentication (password) for sensitive accounts (optional enhancement)
- Invalidate old session when switching accounts

#### B. Device ID Security
- Device ID should be cryptographically random
- Store in httpOnly cookie or localStorage (localStorage is easier for this use case)
- Consider adding device expiration (e.g., 30 days of inactivity)

#### C. Rate Limiting
- Add rate limiting to account switching to prevent abuse
- Limit number of devices per user (optional)

### 5. User Experience Flow

#### Initial Login
1. User logs in with credentials
2. System generates device ID (if not exists)
3. Creates `DeviceAccount` record linking user to device
4. User can now access account switcher

#### Switching Accounts
1. User clicks profile picture → "Switch Account"
2. Modal opens showing list of accounts on this device
3. User selects target account
4. System validates account is associated with device
5. Current session is ended, new session is created for target account
6. User is redirected to home page with new account active

#### Adding New Account
1. User clicks "Add Account" in switcher modal
2. System logs out current user
3. Redirects to login page
4. After login, new account is added to device list
5. User can switch back to previous account

#### Removing Account
1. User clicks "Remove" on an account in the list
2. System deletes `DeviceAccount` record
3. Account is removed from device list
4. User account still exists, just not linked to this device

## Implementation Steps

### Phase 1: Backend Foundation
1. Create `DeviceAccount` model
2. Create and run migrations
3. Create device service (`users/services/device_service.py`)
4. Add signal handler for login tracking
5. Create new views (switch_account, get_device_accounts, remove_account)
6. Add URL patterns

### Phase 2: Frontend Integration
1. Create `device_manager.js` for device ID management
2. Create account switcher modal template
3. Create account list item template
4. Update base template to include device manager
5. Update profile template to add switcher button
6. Add HTMX endpoints for dynamic loading

### Phase 3: Testing & Refinement
1. Test account switching flow
2. Test adding/removing accounts
3. Test across different browsers/devices
4. Verify security measures
5. Polish UI/UX

## Files to Create/Modify

### New Files
- `users/models.py` - Add `DeviceAccount` model
- `users/services/device_service.py` - Device identification service
- `users/templates/users/partials/account_switcher_modal.html` - Switcher modal
- `users/templates/users/partials/account_list_item.html` - Account list item
- `static/js/device_manager.js` - Device ID management
- `users/migrations/XXXX_add_device_account.py` - Migration (auto-generated)

### Modified Files
- `users/views.py` - Add new views
- `users/urls.py` - Add new URL patterns
- `users/signals.py` - Add login tracking signal
- `core/templates/base.html` - Include device manager script
- `users/templates/users/profile.html` - Add switcher button
- `pwaninet/settings/base.py` - No changes needed (using defaults)

## Database Schema Changes

### New Table: `users_deviceaccount`
```sql
CREATE TABLE users_deviceaccount (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    last_used TIMESTAMP NOT NULL,
    session_key VARCHAR(255),
    UNIQUE(user_id, device_id)
);

CREATE INDEX idx_users_deviceaccount_device_id ON users_deviceaccount(device_id);
CREATE INDEX idx_users_deviceaccount_last_used ON users_deviceaccount(last_used DESC);
```

## Edge Cases & Considerations

1. **Multiple Browsers**: Each browser will have its own device ID, so accounts won't sync across browsers (this is expected behavior)
2. **Incognito Mode**: Device ID stored in localStorage won't persist in incognito (acceptable limitation)
3. **Clearing Browser Data**: Clearing localStorage will reset device ID, creating a new device (acceptable)
4. **Account Deletion**: If a user account is deleted, `DeviceAccount` records cascade delete
5. **Session Expiry**: If session expires, user must log in again (standard Django behavior)
6. **Concurrent Sessions**: Multiple devices can be logged into the same account (standard Django behavior)

## Future Enhancements (Optional)

1. **Re-authentication for Switching**: Require password confirmation when switching to sensitive accounts
2. **Device Naming**: Allow users to name their devices (e.g., "My Laptop", "Work Phone")
3. **Device Management Page**: Dedicated page to manage all devices associated with account
4. **Push Notifications**: Notify when account is accessed from new device
5. **Two-Factor Authentication**: Add 2FA requirement for account switching
6. **Account Merge**: Merge multiple accounts into one (advanced feature)

## Testing Checklist

- [ ] User can log in and device account is created
- [ ] User can see list of accounts on device
- [ ] User can switch between accounts successfully
- [ ] User can add new account to device
- [ ] User can remove account from device list
- [ ] Session is properly invalidated on switch
- [ ] Device ID persists across page reloads
- [ ] Security validation prevents switching to unauthorized accounts
- [ ] UI works on mobile and desktop
- [ ] HTMX requests work correctly
- [ ] No console errors in browser

## Estimated Timeline

- **Phase 1**: 2-3 hours
- **Phase 2**: 2-3 hours
- **Phase 3**: 1-2 hours
- **Total**: 5-8 hours

## Notes

- This feature uses localStorage for device ID, which is simple and effective for this use case
- The feature is opt-in - users must explicitly switch accounts
- No changes to existing authentication flow - backward compatible
- All new functionality is additive, doesn't break existing features
