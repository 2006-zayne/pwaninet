# Preferences → Settings Refactor

**Date:** July 3, 2026  
**Status:** Complete  
**Type:** UI/Navigation Refactor

---

## Overview

The application's "Preferences" page has been renamed and restructured as "Settings" to serve as the central hub for all user-configurable features.

---

## Changes Made

### 1. Page Structure

**Before:**
- Single monolithic page: `/users/notification-preferences/`
- Template: `users/notification_preferences.html`
- View: `notification_preferences_view()`

**After:**
- Modular settings hub: `/users/settings/`
- Template: `users/settings.html`
- View: `settings_view()`
- Modular partials in `users/settings/partials/`

### 2. New File Structure

```
users/templates/users/
├── settings.html                          # Main settings page
└── settings/
    └── partials/
        ├── notification_preferences.html  # Notifications section
        └── updates.html                   # Updates section
```

### 3. URL Routing

**New Route:**
- `/users/settings/` → `settings_view` (primary)

**Legacy Route (Redirect):**
- `/users/notification-preferences/` → Redirects to `/users/settings/`

### 4. Navigation Updates

**Profile Page (`users/templates/users/profile.html`):**
- Changed: `<i class="bi bi-bell"></i> PREFERENCES`
- To: `<i class="bi bi-gear"></i> SETTINGS`
- URL: `{% url 'users:settings' %}`

### 5. View Changes

**New View (`users/views.py`):**
```python
@login_required
def settings_view(request):
    """Main settings page with modular sections"""
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('users:settings')
    else:
        form = NotificationPreferencesForm(instance=request.user)
    return render(request, 'users/settings.html', {'form': form})
```

**Legacy View (Redirect):**
```python
@login_required
def notification_preferences_view(request):
    """Legacy view - redirects to new settings page"""
    return redirect('users:settings')
```

---

## Settings Page Architecture

### Current Sections

1. **Notifications**
   - Location: `users/settings/partials/notification_preferences.html`
   - Functionality: Existing notification preferences (unchanged)
   - Fields: Like, Follow, Group Invite, Group Request, Group Approval, Pinch, Email notifications

2. **Updates**
   - Location: `users/settings/partials/updates.html`
   - Functionality: Placeholder for PWA update management
   - Features: Version display, update check, release history (UI only, backend pending)

### Future Sections (Planned)

The modular architecture supports easy addition of:

- **Privacy** - Data privacy settings
- **Security** - Password, 2FA, session management
- **Appearance** - Theme, display preferences
- **Accessibility** - Font size, screen reader options
- **Language** - Language and region settings
- **Account** - Account management, deletion
- **Connected Devices** - Device management
- **Storage** - Storage usage and cleanup
- **About PWANINET** - App information, licenses
- **Developer Options** - Debug features (future)

---

## Backward Compatibility

### URL Redirects

- Old URL `/users/notification-preferences/` automatically redirects to `/users/settings/`
- All existing bookmarks and links will continue to work
- URL name `users:notification_preferences` still resolves (redirects)

### Functionality Preservation

- All notification preference fields remain unchanged
- Form validation logic unchanged
- Database schema unchanged
- No migration required

---

## Implementation Guidelines

### Adding New Settings Sections

1. **Create partial template:**
   ```
   users/templates/users/settings/partials/[section_name].html
   ```

2. **Add navigation item:**
   ```html
   <a href="#[section_name]" class="settings-nav-item">
    <i class="bi bi-[icon]"></i> [Section Name]
   </a>
   ```

3. **Add section to settings.html:**
   ```html
   <section id="[section_name]" class="settings-section">
    <h2 class="settings-section-title">
      <i class="bi bi-[icon]"></i> [Section Name]
    </h2>
    <p class="settings-section-description">[Description]</p>
    {% include 'users/settings/partials/[section_name].html' %}
   </section>
   ```

4. **Update view if needed:**
   - Add form handling if section has form inputs
   - Add context variables if section needs dynamic data

### Section Template Guidelines

- Use the existing CSS variables for consistency
- Follow the card-based design pattern
- Include descriptive text for each setting
- Use Bootstrap Icons for visual cues
- Ensure mobile responsiveness

---

## Testing Checklist

- [x] Navigation from profile page works
- [x] Legacy URL redirects correctly
- [x] Notification preferences form submits successfully
- [x] Form validation works as before
- [x] Success message displays correctly
- [x] Mobile navigation works
- [x] Section navigation highlighting works
- [x] Updates section displays correctly

---

## Migration Notes

### For Developers

- Update any hardcoded references to `notification-preferences` URL
- Use `users:settings` URL name going forward
- Reference the modular partials when adding new sections
- Follow the established CSS variable naming

### For Users

- No action required
- Old bookmarks will redirect automatically
- All notification preferences preserved
- No data loss

---

## Related Documentation

- [PWA Update Manager](../PWA_UPDATE_MANAGER.md) - Updates section will integrate with PWA update system
- [Feature Roadmap](./FEATURE_ROADMAP.md) - Future settings sections planned
- [Architecture](./ARCHITECTURE.md) - Overall application architecture

---

## Future Enhancements

### Short Term
- [ ] Integrate PWA update manager into Updates section
- [ ] Add Privacy section
- [ ] Add Security section

### Medium Term
- [ ] Add Appearance section (theme customization)
- [ ] Add Accessibility section
- [ ] Add Language section

### Long Term
- [ ] Add Connected Devices section
- [ ] Add Storage management section
- [ ] Add Developer Options section

---

## Summary

This refactor establishes Settings as the central hub for user configuration while preserving all existing functionality. The modular architecture enables easy addition of new settings sections without major refactoring.

**Key Benefits:**
- Scalable architecture for future settings
- Better user experience with organized sections
- Backward compatible with existing URLs
- Clear separation of concerns
- Maintainable codebase

**No Breaking Changes:**
- All existing functionality preserved
- Legacy URLs redirect automatically
- No database migrations required
- No user data affected
