# Users app

## Purpose

`users` owns PwaniNet accounts, profile information, authentication-related workflows, account security, privacy choices, and relationships between users.

## Main data

- `User` extends Django's `AbstractUser` and adds academic profile fields, profile/cover photos, biography, profile links, preferences, privacy settings, and online/onboarding state.
- `Follow`, `Pinch`, `Block`, and `HiddenAuthor` represent user relationships and discovery controls.
- `UserSession`, `DeviceAccount`, `UserTwoFactor`, and `RecoveryCode` support session/device management and two-factor/account recovery flows.
- `PlatformInvite` records invitations and referral state.

## Main journeys

Users register through `PwaniSignupForm`, sign in through the project login view, manage their profile and settings, and can use security flows such as two-factor authentication and recovery codes. Profile and post privacy settings feed into discovery and visibility checks. Registration includes username, password, programme, academic level, academic year, and semester; name fields are optional. The privacy notice should disclose these fields accurately.

## Routes and entry points

The app is mounted at `/users/`. Its URLs cover registration, onboarding, profile display/editing, settings, people search, account/device management, and user APIs. Login itself is mounted at `/accounts/login/` and `/login/` by the project URL configuration. Main code lives in `users/models.py`, `users/forms.py`, `users/views.py`, `users/urls.py`, and `users/services/`.

## Developer notes

- The custom user model is configured as the project's authentication model; use `settings.AUTH_USER_MODEL` for model relations.
- User discovery privacy rules are centralized in `users/services/privacy.py` and should be applied consistently to search and recommendation results.
- Registration/authentication views log some identifying and request information. Review logging and retention when changing those flows.
- Profile fields and login behavior affect the Privacy Policy and should be reflected in the pre-launch data inventory.
