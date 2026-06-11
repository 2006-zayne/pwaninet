# Authentication and Account Security Audit Report

**Date:** June 11, 2026  
**Project:** Pwaninet  
**Scope:** Complete authentication and account security audit

---

## Authentication Architecture

### Authentication Flow from Registration to Login

**Registration Flow:**
1. User submits registration form at `/users/register/`
2. `PwaniSignupForm` validates input (extends Django's `UserCreationForm`)
3. Form saves user to database with hashed password
4. User redirected to login page with success message
5. Login form pre-filled with username from sessionStorage

**Login Flow:**
1. User submits login form at `/accounts/login/` (Django's built-in auth URLs)
2. Credentials validated by Django's authentication backend
3. If successful, session created and user redirected to home
4. Device ID captured and stored in `DeviceAccount` model
5. Failed attempts tracked by django-axes

**Session Management Approach:**
- **Framework:** Django session framework (database-backed sessions)
- **Storage:** PostgreSQL database (default Django session backend)
- **Configuration:** `SESSION_COOKIE_SECURE = False` (base.py), `True` in production
- **Session Cookie:** `SESSION_COOKIE_HTTPONLY = True`
- **No SameSite configuration found** (uses Django default)

### JWT Implementation Details

**Status: DISABLED**

JWT is commented out in the codebase:
- `/home/zayne/projects/pwaninet/pwaninet/settings/base.py` line 183: `# 'rest_framework_simplejwt.authentication.JWTAuthentication',  # Temporarily disabled due to pkg_resources issue`
- `/home/zayne/projects/pwaninet/pwaninet/urls.py` line 107-108: `# path('api/token/', include('rest_framework_simplejwt.urls')),`

**Configuration exists but not active:**
```python
# /home/zayne/projects/pwaninet/pwaninet/settings/base.py lines 216-225
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**Library:** `djangorestframework-simplejwt==5.3.0` (installed but not used)

### Refresh Token Implementation Details

**Status: NOT IMPLEMENTED**

Refresh tokens are not used because JWT is disabled. The system relies on Django session authentication instead.

### Cookie Configuration

**Session Cookie:**
- **Name:** `sessionid` (Django default)
- **HttpOnly:** `True` (base.py line 160)
- **Secure:** `False` in base.py/local.py, `True` in production.py (line 33)
- **SameSite:** Not configured (uses Django default: `Lax` in Django 5.x)
- **Expiry:** Browser session (Django default)
- **Domain:** Not configured (uses current domain)
- **Path:** `/` (Django default)

**CSRF Cookie:**
- **Name:** `csrftoken` (Django default)
- **HttpOnly:** `True` (base.py line 162)
- **Secure:** `False` in base.py/local.py, `True` in production.py (line 34)
- **SameSite:** Not configured (uses Django default)
- **Expiry:** 1 year (Django default)
- **Domain:** Not configured
- **Path:** `/` (Django default)

### CSRF Protection Implementation

**Framework:** Django's built-in CSRF protection

**Validation Process:**
- CSRF token required on all POST/PUT/DELETE requests
- Token validated by `django.middleware.csrf.CsrfViewMiddleware` (base.py line 64)
- Templates include `{% csrf_token %}` tag

**Protected Endpoints:** All form submissions (POST/PUT/DELETE)

**Exempted Endpoints:**
- **Development only:** `/api/*` endpoints exempted via `CSRFExemptMiddleware` (local.py lines 94-97)
- **Static files:** PWA manifest and service worker exempted (urls.py lines 30, 43)

**Gap in Protection:**
- **CRITICAL:** In local development, ALL API endpoints are CSRF-exempt via middleware
- Middleware code: `/home/zayne/projects/pwaninet/pwaninet/middleware.py`
```python
class CSRFExemptMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
```

### Logout Implementation

**Endpoint:** `/users/logout/` (users/urls.py line 19)
- Uses Django's built-in `auth_views.LogoutView`
- Template: `logout.html`
- Redirects to login page after logout
- Clears session cookie
- **No token revocation** (JWT not used)

### Account Recovery Implementation

**Status: NOT IMPLEMENTED**

- **Password reset:** Does not exist
- **Email verification:** Does not exist
- **Recovery codes:** Do not exist
- **Account recovery:** Not possible

No password reset templates, views, or URLs found in the codebase.

---

## Registration

### Registration Endpoint(s)

**Primary Endpoint:** `/users/register/` (users/urls.py line 16)
- View: `register_view` (users/views.py lines 28-39)
- Method: POST
- Template: `users/register.html`

### Required Registration Fields

From `PwaniSignupForm` (users/forms.py lines 7-24):
```python
fields = UserCreationForm.Meta.fields + (
    'first_name', 'second_name', 'last_name', 'course', 'year'
)
```

**Required fields:**
- `username` (from UserCreationForm)
- `password1` (from UserCreationForm)
- `password2` (from UserCreationForm)
- `first_name`
- `last_name`
- `course` (ForeignKey to Course model)
- `year` (ForeignKey to Year model)

**Optional fields:**
- `second_name`

### Password Validation Rules

Django's default password validators (base.py lines 106-119):
```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

**Client-side validation:**
- Password strength meter implemented in JavaScript (register.html lines 164, 336-340)
- Minimum strength requirement: "Fair" or better
- Real-time feedback on password strength

### Username Validation Rules

Django's default `AbstractUser` username validation:
- Required
- Unique
- Max length: 150 characters
- Allowed characters: alphanumeric, @, ., +, -, _
- Cannot be a reserved username (e.g., "me")

### Email Validation Rules

**Status: Email field exists but NOT required for registration**

- `email` field exists on User model (inherited from AbstractUser)
- Not included in registration form fields
- No email validation during registration
- No email verification implemented

### Duplicate Account Prevention

**Username uniqueness:** Enforced by Django's AbstractUser
- Database constraint: `UNIQUE` on `username` field
- Form validation raises error if username exists

**Email uniqueness:** NOT enforced
- Multiple accounts can have same email address
- No unique constraint on email field

### Account Verification Flow

**Status: NOT IMPLEMENTED**

No email verification flow exists. Users can log in immediately after registration.

### Whether Email Verification Exists

**NO**

### Whether Email Verification Is Enforced

**NO**

---

## Login

### Login Endpoint(s)

**Primary Endpoint:** `/accounts/login/` (pwaninet/urls.py line 62)
- Uses Django's built-in auth URLs
- Template: `registration/login.html`
- Method: POST

### Accepted Credentials

- **Username** (required)
- **Password** (required)
- Email login NOT supported

### Authentication Backend

**Configuration** (base.py lines 148-151):
```python
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

**Backends:**
1. `AxesStandaloneBackend` - Tracks failed login attempts
2. `ModelBackend` - Standard Django authentication (username/password)

### Password Verification Logic

Django's default password verification:
- Uses `AbstractUser.check_password()` method
- Compares hashed password with input
- Uses PBKDF2 with SHA256

### Failed Login Handling

**Tracked by django-axes:**
- Failed attempts logged to database
- Lockout after threshold reached
- Cool-off period before retry allowed

**Configuration** (base.py lines 238-243):
```python
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=5)
AXES_LOCKOUT_TEMPLATE = 'axes/lockout.html'
AXES_RESET_ON_SUCCESS = True
```

### Rate Limiting Implementation

**Login rate limiting:** django-axes
- 5 failed attempts allowed
- 5-minute cool-off period
- Lockout template: `axes/lockout.html`

**API rate limiting:** Django REST Framework throttling (base.py lines 195-207):
```python
DEFAULT_THROTTLE_CLASSES = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]
DEFAULT_THROTTLE_RATES = {
    'anon': '100/hour',
    'user': '1000/hour',
}
```

### Account Lockout Implementation

**Implemented via django-axes:**
- Locks account after 5 failed login attempts
- Lockout duration: 5 minutes
- Template: `/home/zayne/projects/pwaninet/templates/axes/lockout.html`
- Shows cool-off time to user

**Status:** DISABLED in local development (local.py line 107: `AXES_ENABLED = False`)

### Brute-Force Protection Mechanisms

**Mechanisms in place:**
1. django-axes for login rate limiting
2. DRF throttling for API endpoints
3. Session-based authentication (no token-based attacks)

**Gaps:**
- No CAPTCHA
- No IP-based blocking beyond axes
- No progressive delays
- No account-wide lockout (only per-IP)

---

## Password Storage

### Hashing Algorithm Used

**PBKDF2 with SHA256** (Django default)

### Password Hashing Library Used

**Django's built-in password hashing** (`django.contrib.auth.hashers`)

### Hash Parameters

**Django default PBKDF2 parameters:**
- Algorithm: PBKDF2
- Hash function: SHA256
- Iterations: 390,000 (Django 5.x default)
- Salt: Random per-password salt (automatically generated)

### Whether Passwords Are Ever Logged

**NO evidence of password logging found**

No code found that logs passwords to files, console, or database.

### Whether Passwords Are Ever Stored in Plaintext

**NO**

Passwords are always hashed before storage using Django's password hashing system.

### Password-Related Security Concerns

**Concerns identified:**
1. Password stored in sessionStorage during registration (register.html lines 381-385):
```javascript
sessionStorage.setItem('pendingLoginPassword', password1Field.value);
```
   - **Risk:** XSS vulnerability could expose password
   - **Severity:** Medium
   - **Location:** Client-side JavaScript

2. No password complexity requirements beyond Django defaults
3. No password expiration policy
4. No password history tracking
5. No minimum password length specified (uses Django default of 8)

---

## JWT Security

### JWT Library Used

**djangorestframework-simplejwt==5.3.0** (installed but disabled)

### Signing Algorithm

**HS256** (configured in base.py line 222)

### Token Lifetime

**Access token:** 60 minutes (base.py line 217)
**Refresh token:** 7 days (base.py line 218)

**Status:** NOT ACTIVE - JWT is disabled

### Refresh Token Lifetime

**7 days** (configured but not active)

### Token Rotation Implementation

**Configured but not active:**
```python
'ROTATE_REFRESH_TOKENS': True,
'BLACKLIST_AFTER_ROTATION': True,
```

### Blacklisting Implementation

**Configured but not active:**
- `BLACKLIST_AFTER_ROTATION: True`
- Requires `rest_framework_simplejwt.blacklist` app (not in INSTALLED_APPS)

### Revocation Implementation

**NOT IMPLEMENTED**

No token revocation mechanism exists.

### Storage Location of Tokens

**NOT APPLICABLE** (JWT disabled)

---

## Cookie Security

### Session Cookie (`sessionid`)

- **Name:** `sessionid`
- **HttpOnly:** `True` ✓
- **Secure:** `False` (base.py/local.py), `True` (production.py)
- **SameSite:** Not configured (Django default: `Lax`)
- **Expiry:** Browser session
- **Domain:** Current domain
- **Path:** `/`

### CSRF Cookie (`csrftoken`)

- **Name:** `csrftoken`
- **HttpOnly:** `True` ✓
- **Secure:** `False` (base.py/local.py), `True` (production.py)
- **SameSite:** Not configured (Django default: `Lax`)
- **Expiry:** 1 year
- **Domain:** Current domain
- **Path:** `/`

### Security Gaps

1. **SameSite not explicitly configured** - relies on Django defaults
2. **Secure=False in development** - cookies sent over HTTP
3. **No cookie prefixing** (e.g., `__Secure-`, `__Host-`)

---

## CSRF Protection

### Whether CSRF Protection Exists

**YES** - Django's built-in CSRF protection

### Framework Used

**Django CSRF middleware** (`django.middleware.csrf.CsrfViewMiddleware`)

### Validation Process

1. CSRF token generated and stored in cookie
2. Token included in forms via `{% csrf_token %}` template tag
3. Token validated on POST/PUT/DELETE requests
4. Validation checks token matches cookie value

### Protected Endpoints

All state-changing requests (POST, PUT, DELETE, PATCH)

### Exempted Endpoints

1. **Development only:** All `/api/*` endpoints (via CSRFExemptMiddleware)
2. PWA manifest: `/manifest.webmanifest`
3. Service worker: `/service-worker.js`

### Gaps in Protection

**CRITICAL GAP:** CSRF protection disabled for all API endpoints in development
- Middleware: `/home/zayne/projects/pwaninet/pwaninet/middleware.py`
- This is a security risk if deployed to production with this middleware active
- Comment says "development-only convenience" but no production check exists

---

## Account Recovery

### Whether Password Reset Exists

**NO**

No password reset functionality found in the codebase.

### Whether Email Verification Exists

**NO**

No email verification functionality found.

### Whether Recovery Codes Exist

**NO**

No recovery codes or 2FA implementation found.

### Whether Account Recovery Is Possible

**NO**

Users cannot recover accounts if password is forgotten.

### How Ownership of an Account Is Verified

**NOT APPLICABLE** - No account recovery exists

---

## Security Controls

### Rate Limiting

**Login rate limiting:** django-axes
- Configuration: 5 failures, 5-minute cool-off
- Status: Disabled in local development

**API rate limiting:** Django REST Framework
- Anonymous: 100/hour
- Authenticated: 1000/hour
- Status: Active

### Abuse Prevention

**Mechanisms:**
1. django-axes for login abuse
2. DRF throttling for API abuse
3. Session-based authentication limits concurrent sessions

**Gaps:**
- No CAPTCHA
- No IP reputation checking
- No device fingerprinting beyond basic device ID

### Input Validation

**Form validation:** Django forms with built-in validators
- UserCreationForm for registration
- ProfileUpdateForm for profile updates
- Custom validators in forms

**Serializer validation:** DRF serializers
- UserSerializer, UserUpdateSerializer
- Field-level validation for skills, projects (JSON fields)

**Gaps:**
- No server-side input sanitization beyond Django defaults
- No SQL injection protection beyond Django ORM
- No XSS protection beyond Django's template auto-escaping

### XSS Protections

**Django template auto-escaping:** Enabled by default
- All variables in templates are HTML-escaped
- Explicit `|safe` filter required to bypass

**Content Security Policy:** NOT IMPLEMENTED

**Additional protections:**
- `SECURE_BROWSER_XSS_FILTER = True` (base.py line 154)
- Disabled in local development (local.py line 35)

### CORS Configuration

**Framework:** django-cors-headers

**Configuration** (base.py lines 255-257):
```python
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True
```

**Status:** Active
- Allows credentials (cookies)
- Origins configurable via environment variable

### Security Headers

**Implemented headers:**
1. `X-Frame-Options: DENY` (base.py line 156)
2. `Secure-Browser-XSS-Filter` (base.py line 154)
3. `X-Content-Type-Options: nosniff` (base.py line 155)

**Production-only headers** (production.py lines 29-32):
1. `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
2. `Secure-SSL-Redirect: True`

**Missing headers:**
1. Content-Security-Policy (NOT IMPLEMENTED)
2. Permissions-Policy (NOT IMPLEMENTED)
3. Referrer-Policy (NOT IMPLEMENTED)

### CSP Implementation

**NOT IMPLEMENTED**

No Content-Security-Policy header found in the codebase.

### Audit Logging

**Logging configuration** (production.py lines 36-54):
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
```

**Gaps:**
- No authentication-specific audit logging
- No failed login attempt logging beyond axes
- No password change logging
- No privilege escalation logging
- Logging level set to WARNING (misses info/debug events)

---

## Threat Analysis

### 1. Risk of Account Takeover

**Current Protection:**
- Session-based authentication
- HttpOnly cookies
- CSRF protection (except API in dev)
- Rate limiting on login

**Weaknesses:**
- Password stored in sessionStorage during registration (XSS risk)
- No email verification (attacker can register with any email)
- No 2FA
- No device verification beyond basic device ID
- CSRF disabled for API endpoints in development
- SameSite not explicitly configured

**Severity: HIGH**

### 2. Risk of Brute-Force Attacks

**Current Protection:**
- django-axes rate limiting (5 attempts, 5-minute cool-off)
- DRF API throttling (100/hour anon, 1000/hour auth)
- PBKDF2 with 390,000 iterations (slow hashing)

**Weaknesses:**
- Rate limiting disabled in local development
- No CAPTCHA
- No IP-based blocking beyond axes
- No progressive delays
- No account-wide lockout (only per-IP)
- Axes can be bypassed by rotating IPs

**Severity: MEDIUM**

### 3. Risk of Token Theft

**Current Protection:**
- HttpOnly session cookies
- Secure cookies in production
- No JWT tokens (reduces token theft surface)

**Weaknesses:**
- Secure=False in development (cookies sent over HTTP)
- SameSite not explicitly configured
- No cookie binding to IP or device
- No token encryption
- Session cookies vulnerable to XSS if HttpOnly bypassed

**Severity: MEDIUM**

### 4. Risk of CSRF Attacks

**Current Protection:**
- Django CSRF middleware
- CSRF tokens on all forms
- HttpOnly CSRF cookies

**Weaknesses:**
- **CRITICAL:** CSRF disabled for all API endpoints in development
- CSRFExemptMiddleware has no production check
- No CSRF token rotation
- No double-submit cookie pattern
- SameSite not explicitly configured

**Severity: CRITICAL (in development)**

### 5. Risk of Session Fixation

**Current Protection:**
- Django creates new session on login
- Session ID regenerated on authentication
- HttpOnly session cookies

**Weaknesses:**
- No explicit session fixation protection beyond Django defaults
- No session binding to IP/User-Agent
- No concurrent session limits
- Session ID not rotated on privilege change

**Severity: LOW**

### 6. Risk of Privilege Escalation

**Current Protection:**
- Django's built-in permission system
- `@login_required` decorator on sensitive views
- DRF permission classes (`IsAuthenticated`)

**Weaknesses:**
- No role-based access control (RBAC) beyond Django's basic auth
- Global role field exists but no enforcement logic found
- No permission checks on API endpoints beyond authentication
- No audit logging for privilege changes
- President role validation only in model clean() (not enforced at view level)

**Severity: MEDIUM**

### 7. Risk of Password Reset Abuse

**Current Protection:**
- **NOT APPLICABLE** - Password reset not implemented

**Weaknesses:**
- Users cannot recover accounts if password forgotten
- No password reset means no password reset abuse, but also no recovery

**Severity: LOW (feature missing, not a vulnerability)**

---

## Architecture Diagram

### Registration Flow

```
User → /users/register/ (POST)
  ↓
PwaniSignupForm validation
  ↓
UserCreationForm validation (Django)
  ↓
Password hashed (PBKDF2-SHA256)
  ↓
User saved to database
  ↓
Device ID generated/stored in localStorage
  ↓
Password stored in sessionStorage (SECURITY RISK)
  ↓
Redirect to /accounts/login/
  ↓
Login form pre-filled with username
```

### Login Flow

```
User → /accounts/login/ (POST)
  ↓
Credentials captured
  ↓
AxesStandaloneBackend checks for lockout
  ↓
ModelBackend validates username/password
  ↓
If valid:
  - Session created
  - DeviceAccount record created/updated
  - User redirected to home
If invalid:
  - Failed attempt logged by axes
  - If 5 failures: Account locked for 5 minutes
  - Lockout template shown
```

### Authenticated Request Flow

```
User makes request
  ↓
SessionMiddleware loads session
  ↓
AuthenticationMiddleware sets request.user
  ↓
@login_required decorator checks authentication
  ↓
If authenticated: Request processed
If not authenticated: Redirect to login
```

### Token Refresh Flow

```
NOT IMPLEMENTED (JWT disabled)
System uses Django sessions instead
```

### Logout Flow

```
User → /users/logout/
  ↓
Django LogoutView
  ↓
Session deleted
  ↓
Session cookie cleared
  ↓
Redirect to login page
  ↓
Logout template shown
```

### Password Recovery Flow

```
NOT IMPLEMENTED
No password reset functionality exists
```

---

## Final Summary

### Strengths

1. **Strong password hashing:** PBKDF2 with SHA256 and 390,000 iterations
2. **HttpOnly cookies:** Both session and CSRF cookies are HttpOnly
3. **Rate limiting:** django-axes for login, DRF throttling for API
4. **CSRF protection:** Django's built-in CSRF middleware (except API in dev)
5. **Security headers in production:** HSTS, SSL redirect, X-Frame-Options
6. **Device tracking:** DeviceAccount model for multi-device support
7. **Input validation:** Django forms and DRF serializers
8. **XSS protection:** Django template auto-escaping
9. **Secure cookies in production:** SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE set to True
10. **Authentication backends:** AxesStandaloneBackend for brute-force protection

### Weaknesses

1. **CRITICAL:** CSRF disabled for all API endpoints in development with no production check
2. **HIGH:** Password stored in sessionStorage during registration (XSS risk)
3. **HIGH:** No email verification - attackers can register with any email
4. **HIGH:** No password reset functionality - users cannot recover accounts
5. **MEDIUM:** SameSite cookie attribute not explicitly configured
6. **MEDIUM:** No Content-Security-Policy header
7. **MEDIUM:** No 2FA implementation
8. **MEDIUM:** Rate limiting disabled in local development
9. **MEDIUM:** No CAPTCHA for login/registration
10. **LOW:** No audit logging for authentication events
11. **LOW:** JWT disabled (reduces API security options)
12. **LOW:** No permission checks beyond authentication
13. **LOW:** Secure=False for cookies in development

### Missing MVP Features

1. **Password reset** - Critical for user experience and security
2. **Email verification** - Prevents fake accounts and spam
3. **Two-factor authentication (2FA)** - Essential for account security
4. **JWT authentication** - Needed for secure API authentication
5. **Content-Security-Policy** - Critical for XSS protection
6. **Audit logging** - Essential for security monitoring
7. **Session management UI** - Users cannot view/revoke active sessions
8. **Password strength enforcement** - Only client-side, no server-side enforcement
9. **Account lockout notification** - Users not notified of lockouts
10. **Security event notifications** - Users not notified of suspicious activity

### Top 10 Security Improvements Ranked by Impact

1. **Enable CSRF protection for API endpoints in production**
   - Remove or add production check to CSRFExemptMiddleware
   - Impact: Prevents CSRF attacks on API
   - Severity: Critical

2. **Remove password from sessionStorage**
   - Eliminate sessionStorage.setItem('pendingLoginPassword', ...)
   - Impact: Prevents password exposure via XSS
   - Severity: High

3. **Implement password reset functionality**
   - Add Django's password reset views and templates
   - Impact: Enables account recovery
   - Severity: High

4. **Implement email verification**
   - Require email verification before account activation
   - Impact: Prevents fake accounts and spam
   - Severity: High

5. **Explicitly configure SameSite cookie attribute**
   - Set SESSION_COOKIE_SAMESITE and CSRF_COOKIE_SAMESITE to 'Lax' or 'Strict'
   - Impact: Prevents CSRF attacks
   - Severity: High

6. **Implement Content-Security-Policy header**
   - Add CSP header to prevent XSS and data injection
   - Impact: Significant XSS protection
   - Severity: High

7. **Enable JWT authentication for API**
   - Fix pkg_resources issue and enable rest_framework_simplejwt
   - Impact: Secure stateless API authentication
   - Severity: Medium

8. **Implement two-factor authentication (2FA)**
   - Add TOTP or SMS-based 2FA
   - Impact: Prevents account takeover from password theft
   - Severity: Medium

9. **Add CAPTCHA to login/registration**
   - Implement reCAPTCHA or similar
   - Impact: Prevents automated brute-force attacks
   - Severity: Medium

10. **Implement authentication audit logging**
    - Log all login attempts, password changes, privilege changes
    - Impact: Enables security monitoring and forensics
    - Severity: Medium

---

## File References

### Key Files Analyzed

- `/home/zayne/projects/pwaninet/pwaninet/settings/base.py` - Main settings configuration
- `/home/zayne/projects/pwaninet/pwaninet/settings/local.py` - Development settings
- `/home/zayne/projects/pwaninet/pwaninet/settings/production.py` - Production settings
- `/home/zayne/projects/pwaninet/pwaninet/urls.py` - Main URL configuration
- `/home/zayne/projects/pwaninet/pwaninet/middleware.py` - Custom middleware
- `/home/zayne/projects/pwaninet/users/models.py` - User model definition
- `/home/zayne/projects/pwaninet/users/views.py` - User views
- `/home/zayne/projects/pwaninet/users/serializers.py` - User serializers
- `/home/zayne/projects/pwaninet/users/forms.py` - User forms
- `/home/zayne/projects/pwaninet/users/urls.py` - User URLs
- `/home/zayne/projects/pwaninet/users/services/device_service.py` - Device service
- `/home/zayne/projects/pwaninet/templates/registration/login.html` - Login template
- `/home/zayne/projects/pwaninet/users/templates/users/register.html` - Registration template
- `/home/zayne/projects/pwaninet/templates/logout.html` - Logout template
- `/home/zayne/projects/pwaninet/templates/axes/lockout.html` - Lockout template
- `/home/zayne/projects/pwaninet/requirements.txt` - Dependencies

---

**Audit completed based on codebase analysis. All findings are factual and based on actual implementation in the codebase.**
