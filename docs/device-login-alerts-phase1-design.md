# Phase 1 Design — New-Device Login Alerts & Device Management (non-blocking)

Companion to: `docs/linked-accounts-and-device-alerts.md` (overall plan)
Status: **Design spec (pre-implementation)**

Flow order agreed: **notification first → tap → approval sheet modal.** The modal is never shown unprompted; it only opens from an in-app notification card, a FCM push tap, or the Security/Devices settings page.

---

## 1. Data flow (end to end)

```
Login succeeds
  └─ create_or_update_session()                    [users/services/session_service.py, hook exists]
       ├─ existing session (created=False)         → update as today, stop
       └─ new session (created=True)
            ├─ device_hash in TrustedDevice        → silent, log only
            ├─ device_hash in BlockedDevice        → block middleware kills it immediately
            ├─ user has NO trusted device yet      → auto-trust bootstrap, log only
            └─ unknown device                      → DeviceVerificationService.send_challenge()
                  ├─ DeviceVerificationEvent(status=pending)
                  ├─ publish SECURITY_LOGIN_DETECTED platform event (context: challenge)
                  ├─ NotificationObject (SECURITY / CRITICAL) + NotificationActions
                  └─ delivery engine → FCM push + in-app + email fallback
                        └─ user taps card / push → deep link opens approval sheet
                              ├─ "Yes, it was me"      → TrustedDevice created (promote)
                              └─ "No, it wasn't me"    → confirm step
                                   ├─ Block device     → kill session + BlockedDevice
                                   └─ Block device + nuke → + revoke all other
                                        sessions (except trusted) + force password
                                        reset + confirmation email
```

## 2. Models (new, `users/models.py`)

### TrustedDevice
```python
user FK users.User, null=False, related_name='trusted_devices', indexed
device_hash CharField(64), db_index          # output of hash_device_id() with pepper
nickname CharField(100), blank=True          # user-editable later; default from device_name
is_primary BooleanField, default=False      # first trusted device becomes primary automatically
device_name CharField(255), blank=True      # snapshot at trust time ("iPhone 15 Pro…")
trusted_at DateTimeField(auto_now_add=True)
last_confirmed_at DateTimeField(null=True, blank=True)
source_event FK DeviceVerificationEvent, null=True, on_delete=SET_NULL
```
- `unique_together ('user', 'device_hash')`
- Invariant: at most one `is_primary` per user (enforced in service; unset others on promote).

### DeviceVerificationEvent
```python
user FK users.User, related_name='device_verifications', indexed
device_hash CharField(64), db_index
device_type CharField(20)  (mobile/tablet/desktop, choices as UserSession)
device_name CharField(255)                  # e.g. "iPhone 15 Pro (Safari)
browser CharField(100)
operating_system CharField(100)
ip_address GenericIPAddressField(null=True)
location_city CharField(100), blank
location_country CharField(100), blank      # rendered together as "Nairobi, KE (approx.)"
location_source CharField(20) = 'ip'        # future-proof for gps source
session_key CharField(255), blank           # FK-ish to the UserSession row
notification FK notifications.NotificationObject, null=True, on_delete=SET_NULL
channel CharField(20): push / in_app / email
status CharField(20): pending / approved / rejected / expired   (default pending, indexed)
expires_at DateTimeField                    # created + 24h
responded_at DateTimeField(null=True)
responded_from_device_hash CharField(64), blank   # security audit: which device acted
created_at, updated_at
```
- `unique_together` **(user, session_key)** for pending rows only via service-level guard (prevents duplicates from retries).

### BlockedDevice
```python
user FK users.User, related_name='blocked_devices', indexed
device_hash CharField(64), db_index
reason CharField(20): user_reported / suspected_abuse (default user_reported)
source_event FK DeviceVerificationEvent, null=True, on_delete=SET_NULL
created_at DateTimeField(auto_now_add=True)
```
- Store the **hash only**, never raw device IDs or IPs beyond the audit row.

## 3. Hook into login detection

Point: `users/services/session_service.py :: create_or_update_session`, right after `user_session, created = ...`.

Rules:
1. `created=False` → nothing (session updates must never re-challenge).
2. `device_hash` missing (no cookie possible, bots) → graceful no-op, log.
3. Device already `TrustedDevice` for user → no-op (log `[SECURITY-DEVICE] trusted`).
4. Device `BlockedDevice` → mark session for termination (middleware sees it within the same request; also call `revoke_session` directly here — belt and braces).
5. User has zero `TrustedDevice` rows → **bootstrap**: create `TrustedDevice` (this is the first device after rollout or the first signup device), log, no notification. This prevents alert-storms on rollout day and the chicken-and-egg problem.
6. Otherwise → `device_alert_service.send_challenge(user, request, user_session, device_hash)`.

The service file: `users/services/device_alert_service.py` — detection logic, challenge send, `respond()`, `kill_chain()`.

## 4. Notification & push design

### Platform event
Add to `notifications/events/registry.py` (Security section):
```python
SECURITY_DEVICE_LOGIN_NEW = "security.device.login_new"       # fired per challenge
SECURITY_DEVICE_TRUSTED = "security.device.trusted"           # user approved
SECURITY_DEVICE_BLOCKED = "security.device.blocked"           # user rejected
```
Then publish through the existing `publisher` — no new transport code.

### NotificationObject
- `notification_type = SECURITY`, `category = SECURITY`, `priority = CRITICAL`
- Body copy (title + text): title **"New sign-in detected"**; body: `"{device}, {location} · {time}"`.
- Delivery is exempt from any user "security notifications off" preference — security alerts are always on (documented in NotificationPreference rules).

### NotificationAction rows (first-class, existing model)
| order | action_type | label | method | url | is_primary |
|---|---|---|---|---|---|
| 1 | `ACCEPT` | Yes, it was me | POST | `/users/api/security/device-verifications/{id}/respond/` payload `{decision:"approve"}` | ✔ |
| 2 | `DECLINE` | It wasn't me | POST | same URL, payload `{decision:"deny"}` | — |

### FCM push (data message, android/web)
```json
{
  "kind": "device_verification",
  "event_id": "<uuid>",
  "notification_id": "<uuid>",
  "deep_link": "/users/security/device-verifications/<event_id>/",
  "title": "New sign-in detected",
  "body": "iPhone · Safari · Nairobi, KE (approx.)"
}
```
- Android (Capacitor): background tap → open the deep-link route in the app shell.
- Desktop web push: click → open the same URL in a tab; page auto-opens the bottom sheet on load (`?sheet=device-verification` param support).

## 5. Approval sheet (bottom-sheet modal)

Template: `users/templates/users/partials/device_verification_sheet.html` (bottom-sheet styling matching the Google sign-in sheet pattern and `push_notification_bottom_sheet.html`).

Routes:
- `GET /users/security/device-verifications/<uuid>/` → HTML partial (content only, for HTMX/sheet injection). Full-page fallback renders centered card if opened directly.
- `POST /users/api/security/device-verifications/<uuid>/respond/` → JSON, CSRF token required, rate-limited.

### Sheet states (single template, state-driven)

**State A — pending (device info card)**
- Title: **New sign-in detected** / subtitle: *A device just signed in to your Vasto account*
- Device rows (verbatim copy):
  - Device: `iPhone 15 Pro · Safari on iOS 18` (type icon switched by device_type)
  - Location: `Nairobi, Kenya (approx.)` — hidden row for unknown-public-IP case
  - Time: `Sat 17 Oct 2026, 05:42 EAT` (local, `humanize` + explicit tz)
  - IP: `196.x.x.x` masked (e.g. `196.202.***.11`) — enough for the user to judge, not precise
- Note: *A sign-in is not a password leak — 2FA still protects your account.*
- Primary button (green): **Yes, it was me** → approve
- Secondary button (red outline): **No, it wasn't me** → state B
- Inline state: if request's own device hash == event's `device_hash` → buttons disabled with note: *"Approve this sign-in from one of your trusted devices."* (prevents attacker self-approving)

**State B — deny confirm (2-step, requires explicit choice)**
- Title: **Block this device and secure your account?**
- Option 1 — **Block device**: sign out on that device and block its ID.
- Option 2 — **Block device + secure my account (Nuke)**: also sign out everywhere (trusted devices stay), require a password reset before the next sign-in, and email you the summary.
- Buttons: `Back` / two stacked destructive options. Denial of either path ALSO kills the event's session immediately at POST time (step B confirms escalation only).

**State C — approved**
- ✔ **Device trusted** — "You'll stop getting alerts for this device." Optional: give it a nickname now (input + save).

**State D — rejected**
- 🛡 "We blocked that device + summary of exactly what was done" (nuclear path spells out: sessions revoked, password reset required, email sent).

**State E — expired / already acted / not allowed**
- Small status paragraph, no buttons.

## 6. Respond endpoint & kill chain

`users/services/device_alert_service.py :: respond(event, decision, escalation, acting_request)`:

Guards (each fails → 403 JSON): event status == pending · event not expired · acting user == event.user · **acting device hash != event.device_hash** · CSRF ok · per-user rate limit (reuse `GOOGLE_COMPLETE_RATELIMIT_*` pattern).

Outcomes:
- `approve` → mark approved, `TrustedDevice.get_or_create` (+ primary if none), publish `SECURITY_DEVICE_TRUSTED`, mark notification actioned.
- `deny (block)` → mark rejected → `block_device(event)`:
  1. `BlockedDevice.objects.get_or_create(user, device_hash, reason=user_reported)`
  2. kill the event's session (`revoke_session(session_key)`)
  3. publish `SECURITY_DEVICE_BLOCKED`, notify in-app + email summary
- `deny (nuke)` = block_device + secure_account:
  4. revoke ALL user sessions except sessions bound to `TrustedDevice` hashes
  5. set `User` flag/salt so existing password becomes invalid until reset (rotate password hash to unusable, exclude from auto-login paths), email the password reset link
  6. email: full inventory (blocked device, revoked sessions, reset email, "if this was you, contact support")

## 7. Enforcement middleware

`pwaninet/middleware/device_block_middleware.py`, placed right after `AuthenticationMiddleware`:
- Authenticated session requests only: resolve device hash (cheap cookie read + hash computation, no DB hit unless changed); on hash-in-blocked-set → `logout()` + redirect to login with a message ("This device has been blocked from your account").
- Keep a small per-request cache `user_id -> set(blocked hashes)` (same pattern as preferences caching in the codebase).

## 8. Devices settings page additions

`settings_active_devices_view` gains three things:
1. Trusted-badge chip on sessions whose device is trusted + "Make primary" action (swaps `is_primary`).
2. `TrustedDevice` list row group: nickname, trusted date, "Untrust" (reverts to alert-on-next-login; requires password confirm if it's the *only* trusted device and user has push capable devices — same philosophy as unlink protection).
3. Blocked devices section: hash-named entries ("Device blocked · 17 Oct 2026"), "Unblock" (password confirm).

## 9. Expiry

Celery-beat task (registered beside existing `tasks.py` entries): every 15 min, `pending` & `expires_at < now` → status=expired, expire the NotificationObject (mark read/dismissed), optional quiet email fallback if FCM channel was chosen but had no subscription reach.

## 10. What devices can act on what

| Acting device | Can approve | Can deny |
|---|---|---|
| Any TrustedDevice (web + app) | ✔ | ✔ |
| The挑战 new device itself | ✘ (disabled in UI, rejected in API) | ✘ |
| Untrusted OTHER device | ✘ | ✘ (show sheet, disabled) |

## 11. Tests

Following `users/tests.py` / `notifications/tests.py` patterns:
- Detection: new session → event created exactly once (retry idempotency); update → no event; trusted → none; bootstrap on zero trusted.
- Respond guards: wrong device, wrong user, expired, double-act, unauthenticated, CSRF absent.
- Kill chain: session killed, blocked hash blocks login (middleware), revoke-all spares trusted, password unusable until reset, emails sent (one per path).
- Notification: SECURITY object created, actions correct, FCM payload shape, expiry task.
- Sheet routes: pending/expired/unauthenticated renders.

## 12. File touchlist

| File | Change |
|---|---|
| `users/models.py` | +3 models |
| `users/migrations/00XX_*.py` | migration |
| `users/services/device_alert_service.py` | NEW — detection/challenge/respond/kill chain |
| `users/services/session_service.py` | hook call after session create |
| `users/views.py`, `users/urls.py` | sheet GET + respond POST (2 routes) |
| `users/templates/users/partials/device_verification_sheet.html` | NEW |
| `settings_privacy_devices.html` (devices page) | trusted/blocked sections |
| `notifications/events/registry.py` | +3 event types |
| `notifications/tasks.py` (or celery beat schedule) | expiry task |
| `pwaninet/middleware/device_block_middleware.py` | NEW + settings MIDDLEWARE |
| Settings | `DEVICE_VERIFICATION_EXPIRY_HOURS`, `DEVICE_ALERT_EMAIL_FALLBACK`, GeoIP path env |

**Out of scope for Phase 1:** blocking challenge (Phase 3), GPS location, token-auth (no session) logins, admin analytics on abused devices.
