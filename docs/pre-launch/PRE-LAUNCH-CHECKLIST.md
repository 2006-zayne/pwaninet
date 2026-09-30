# PwaniNet Pre-launch Documentation and Compliance Checklist

Internal working document. This is a planning checklist, not a claim of legal compliance. See [the open-issues list](OPEN-ISSUES.md) for findings and follow-up work. Do not include its internal notes in student-facing documents.

## Agreed product scope

- Launch scope includes the current PwaniNet features except direct messaging, which is frozen until further notice.
- Planned student-facing documents: About PwaniNet, Privacy Policy, and a short licence/attribution notice.
- Privacy Policy link planned for the login page and Settings → About.
- Settings → About already contains a placeholder Licenses section; required third-party notices still need to be inventoried and presented.
- The project is associated with Pwani University in its intended audience and name, but no written University approval has been received yet.
- Operator disclosure should state that Zayne Earthman is a Pwani University student and PwaniNet is an independent personal project, not a University assignment or official University service.
- Public operator name: Zayne Earthman.
- Public contact for support, privacy, and content-rights reports: Engineerzayne005@gmail.com.
- Intended eligibility: students enrolled at Pwani University, regardless of age; current registration has no age check. Confirm safeguards for any student who is legally a child.
- Keep source assets in `static/` under version control; generated `staticfiles/` and uploaded media stay out of Git.
- Student pain points are currently described as fragmented campus updates/discussions and difficulty finding relevant study resources or connecting with peers. Validate this wording with student experience before presenting it as research-backed.

## Before publishing About or Privacy Policy

- Public-copy rule: the About page, Privacy Policy, and short licence notice must address students in a finished reader-facing voice. Keep repository findings, unresolved questions, implementation defects, and instructions to the operator in this internal checklist only.

- [x] Confirm the operator's public contact details and working privacy/support contact; record any applicable ODPC registration details.
- [ ] Confirm whether PwaniNet is independent, authorized, sponsored, or otherwise affiliated; obtain written University guidance before making affiliation claims.
- [ ] Ask Pwani University about using its name, logo, marks, and visual identity in the service and promotional material.
- [ ] Obtain and review the current University Intellectual Property Rights, ICT, library/exam-bank, and student conduct/academic integrity policies relevant to PwaniNet.
- [ ] Confirm the applicable ODPC registration category and any registration duties for the operator and relevant processors. Record the decision and any registration details.
- [ ] Confirm the lawful basis, stated purposes, and user notice/consent flows for each personal-data use.
- [ ] Inventory production data flows and actual recipients, including hosting, database, backups, email, push, CDN/object storage, error logs, analytics, and any AI providers.
- [ ] Identify storage and processing locations and verify safeguards for any transfer of personal data outside Kenya.
- [ ] Confirm the live signup form matches the documented fields: username, password, programme, academic level, academic year, semester, and optional name fields. Confirm whether email is collected anywhere before describing it as collected data.
- [ ] Review password handling, authentication logs, IP/user-agent collection, session/device records, and retention; resolve the session-storage password concern before making security claims.
- [ ] Set retention periods for account data, user content, logs, notification tokens, backups, and deleted accounts. Account settings now offer erase-content or anonymize-content choices; review cascade scope and rehearse on disposable data before launch.
- [ ] Define access, correction, objection, deletion, account closure, and complaint workflows, including a responsible person and response tracking.
- [ ] Document safeguards for any student user who is legally a child; eligibility is limited to enrolled Pwani University students, with no age cutoff or age check in the current signup flow.
- [ ] Confirm messaging is inaccessible/disabled in the production launch, not merely described as frozen.
- [ ] Identify cookies and browser storage used by the production site, and determine whether any consent notice is needed for optional tracking.
- [ ] Confirm accessible contact routes for privacy requests, support, and reports.

## User content and intellectual property

- [ ] Publish clear upload rules requiring users to have rights or permission to share content.
- [ ] Explain that contributions are associated with the publishing account, remind users to post carefully, and accurately describe visibility and the limits of deletion after others copy content.
- [ ] Define a narrow service licence for user content (hosting, displaying, and distributing within the service based on selected visibility); do not imply ownership transfers to PwaniNet.
- [ ] Confirm image/photo permissions and provide a process for a person depicted in an image to report it.
- [ ] For past papers, lecture notes, slides, and other university materials, obtain written permission or verify another valid legal basis before rehosting. Prefer official University links where possible.
- [ ] Keep provenance, author/owner, permission, and licence records for materials published by PwaniNet.
- [ ] Create a copyright/privacy report-and-review process with a public contact and a clear removal or restriction workflow.
- [ ] Review the bundled fonts, packages, icons, images, and other assets; preserve required licence and attribution notices.
- [x] Keep the default avatar in tracked `static/images/` and map the legacy profile-image default to that static asset; keep uploaded user media out of Git.
- [ ] Decide whether separate user-facing Terms of Use and Community/Content Rules are required before public registration and uploads.

## Site implementation after drafts are approved

- [ ] Add a public About PwaniNet page.
- [ ] Add a public Privacy Policy page and link it from login and Settings → About.
- [ ] Replace the placeholder Licenses section with the reviewed short notice and verified third-party notices/attributions.
- [ ] Make sure the content reporting/privacy contact is easy to find.
- [ ] Check the pages in both web and mobile/PWA flows and in supported languages.
- [ ] Set the effective date and a method for tracking policy changes.
