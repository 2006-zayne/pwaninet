# Linked Accounts & New-Device Login Alerts — Implementation Plan

Status: **Plan (agreed scope, not yet implemented)**

Decisions locked in:

| Decision | Choice |
|---|---|
| Approval flow | **Non-blocking** — login succeeds immediately, alert sent to trusted device, "No" = kill + block |
| OAuth approach | **Hand-rolled**, extending `users/services/google_auth_service.py` pattern (not django-allauth) |
| Providers in scope | Google (exists), **GitHub, LinkedIn** |
| Location source | **IP geolocation only** (MaxMind GeoIP2 offline DB, approximate phrasing) |

---

## Feature A — Linked accounts (social linking)

### Existing groundwork
- `GoogleAccount` model (`users/models.py`) — `sub`-keyed (never email matching), `link_method` enum
- `users/services/google_auth_service.py` — JWKS ID-token verification, pending-stash helpers, rate limiting
- Views: `google_complete`, `google_link`, `google_redirect` (`users/urls.py`)
- 2FA (TOTP + recovery codes) already built — social login must respect the 2FA gate

### Changes

1. **Generalize the model.** New `SocialAccount`:
   `user (FK), provider (choices: google/github/linkedin), provider_uid, email, email_verified, extra_data (JSON), link_method, created_at, last_login_at`
   - `unique_together ("provider", "provider_uid")`
   - Data migration copies all `GoogleAccount` rows (`provider_uid = sub`); `GoogleAccount` retired after burn-in period
2. **`SocialAccount` service layer.** `users/services/social_auth_service.py` with per-provider adapters exposing a common interface:
   `authorize_url(state, redirect_uri)`, `exchange_code(code, redirect_uri)`, `verify_token(...)`, `fetch_profile(...)`
   - Google keeps its existing GIS popup ID-token flow as one adapter's special case
   - GitHub/LinkedIn use the standard redirect OAuth2 authorization-code flow
3. **New URLs per provider.**
   - `users/<provider>/connect/` — login-or-link entry, generates + stashescsrf `state` in session
   - `users/<provider>/callback/` — binds `state`, exchanges code, then either completes signup, links to the logged-in user (explicit link only when a session exists), or requires password/2FA confirmation when the provider's verified email collides with an existing local account (anti account-takeover rule)
4. **Settings UI.** New section *Settings → Privacy → Connected accounts* (mirrors the two-factor section pattern):
   - List linked providers, link new, unlink
   - **Unlink protection:** password confirmation required; refuse to unlink the last remaining credential (no password + last social link = lockout)
5. **Session/notify side effects.** Linking/unlinking emits a notification; unlink revokes sessions created via that provider's logins.

### External setup required (user action)
- GitHub OAuth App → `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`; callback `{BASE_URL}/users/github/callback/`
- LinkedIn app (OpenID Connect product) → `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`; redirect `{BASE_URL}/users/linkedin/callback/`

---

## Feature B — New-device login alerts + approve/block

### Existing groundwork
- `UserSession` (IP, UA, device type, browser, OS, location), `DeviceAccount`, `device_service` (hashes device IDs), `AuthLoggingMiddleware`
- Notifications app: event publisher/registry, delivery engine + adapters, `PushSubscription` (FCM, has `device_id`)
- Settings → Privacy → Devices page + `api_sign_out_session` / sign-out-all APIs

### Models (additive)

1. **`TrustedDevice`** — `user FK, device_id_hash (unique), nickname, is_primary, push_subscription FK, trusted_at, last_confirmed_at`
   - **Bootstrapping:** first login per user with zero trusted devices → auto-trust that device, alert data recorded but delivery is email-only (no push target exists yet)
2. **`DeviceVerificationEvent`** — `user, device_id_hash, ip, user_agent, geo, channel (in_app/push/email), response (approved/rejected/expired/pending), created_at, responded_at`
   - Audit trail of every challenge; unresponded events auto-expire after 24h
3. **`BlockedDevice`** — `user FK, device_id_hash, reason, created_at`
   - Stores **hashed** fingerprint only (device IDs are client-supplied and spoofable; hash with `SECRET_KEY`-derived pepper and treat as a signal, never as authentication — 2FA remains the gate)

### Flow (non-blocking)

1. Login succeeds immediately → `UserSession` created as today, plus a `DeviceVerificationEvent` + `DeviceLoginEvent` published
2. Delivery engine fans out to trusted device's `PushSubscription` (FCM, deep-link payload carrying event ID) + in-app inbox; email fallback
3. **"Yes, it was me"** → device promoted to `TrustedDevice`
4. **"No, it wasn't me"** → kill chain:
   - Kill the offending session (reuse sign-out machinery)
   - Block the device hash (rejected at middleware for fresh logins + existing session)
   - Revoke all other sessions except trusted devices
   - Force password reset + email confirmation of actions taken
5. Alert copy uses approximate location ("Nairobi, KE (approx.)")

### Enforcement & UI
- Small hook in the middleware layer rejecting sessions/logins whose device hash is blocked
- *Settings → Privacy → Devices* gains: trusted badge, set-primary action, blocked-device history
- Approval can never be granted from the device being verified

### External setup required
- MaxMind GeoLite2-City offline DB file (needs a free license key at maxmind.com)

---

## Build order

1. **Phase 1 (device alerts):** `TrustedDevice` + `DeviceVerificationEvent` + `BlockedDevice` models, login detection, FCM + in-app alert, approve/reject actions + kill chain, devices settings UI
2. **Phase 2 (social):** `SocialAccount` generalization + Google migration, GitHub + LinkedIn adapters/callbacks, Connected-accounts settings UI, unlink protection
3. **Phase 3 (optional later):** WhatsApp-style blocking challenge, other providers
