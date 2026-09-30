# Recommendations app

## Purpose

`recommendations` supplies recommendation services for users, groups, and academic documents. It is a service module rather than a model-heavy app.

## Main implementation

Recommendation logic is under `recommendations/services/`, including user, group, document recommenders and a shared engine. The app has no dedicated URL configuration in the root URL map; other parts of the site call its services.

## Developer notes

- Treat recommendations as candidate suggestions, not authorization. The destination view/API must still enforce access and visibility.
- Respect blocks, profile privacy, hidden authors, group membership, and document availability when assembling candidates.
- Avoid exposing private interaction history through ranking or explanation text.
- Update this guide if recommendation endpoints or persistent models are introduced.
