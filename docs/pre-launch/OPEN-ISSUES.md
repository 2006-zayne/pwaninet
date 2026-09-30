# Pre-launch open issues

Internal operator/developer document. Do not link this file from the student-facing site. Keep unresolved findings and implementation tasks here; keep About, Privacy, and licence copy written for students.

## Privacy and account handling

- **Signup field alignment:** the Privacy Policy now lists username, password, programme, academic level, academic year, semester, and optional name fields. Compare the deployed signup form and required/optional status with this description before publishing.
- **Password flow:** the repository review raised a concern that one registration path may place a password in browser session storage. Verify the live flow and remove unsafe temporary password storage before making security assurances.
- **Retention and account closure:** a profile-settings deletion form now offers account-and-content erasure or profile/sign-in removal while keeping authored content under a generic account name. Review the cascading deletion scope, execute a cleanup rehearsal on disposable data, and define retention periods for logs and backups; implement the access, correction, objection, and deletion-request tracking process.
- **Technical data inventory:** confirm actual IP address, browser/device, session, login, diagnostic, and security data collected by the deployed service and its infrastructure. Set retention periods and make the Privacy Policy precise enough to match.
- **Cookies and browser storage:** verify all cookies, local/session storage, analytics, and push-notification storage in the production web and mobile flows.
- **Children:** eligibility has no age cutoff and is limited to students enrolled at Pwani University. Decide safeguards and handling for any student user who is a child before launch.
- **Privacy requests:** confirm the supplied email is monitored and establish a practical request/complaint workflow and response owner.
- **Legal basis and registration:** document the lawful basis for each purpose, determine any applicable ODPC registration requirements, and review cross-border processing obligations.

## Providers, storage, and security

- **Live service inventory:** identify the actual hosting, database, backup, email, push, CDN/object storage, logging/monitoring, analytics, and AI providers. Repository configuration alone does not show what is active.
- **Activity analytics retention:** the admin dashboard now records account-linked daily activity heartbeats for active-user metrics. Set and document a retention period for these records.
- **Locations and transfers:** record where personal information is stored or processed and verify safeguards for transfers outside Kenya.
- **Upload storage:** verify production uploads use the intended object storage/CDN, including private-document access controls. Current settings also support local filesystem storage.
- **Private media delivery:** the configured R2/CDN mode currently disables signed reads for a public bucket. Post/profile visibility checks do not protect a media URL copied directly from that CDN. Restricted post and profile media need private storage and authorization-aware or short-lived signed delivery before claiming those privacy levels fully protect media.
- **Security claims:** complete a launch review of authentication, authorization, secrets, logging, backup access, and incident response. Keep public security wording limited to verified practices.

## University relationship, user content, and rights

- **University relationship and name:** no written University approval has been received. Ask the University about use of its name, marks, logo, and visual identity, and avoid claims of endorsement or affiliation unless approved in writing.
- **University rules:** review applicable student conduct, ICT, academic integrity, intellectual property, library, and examination-bank rules.
- **Academic materials:** do not rehost past papers, lecture notes, slides, or other University materials until permission or another valid legal basis is confirmed; prefer official links where possible.
- **Photos and user content:** establish upload rules, attribution/provenance records where appropriate, and a clear privacy/copyright report, review, and removal process. Keep the reminder that users are responsible for what they publish under their accounts.
- **User-content permission:** settle terms describing the limited permission needed to host and display content, without implying a transfer of ownership.

## Licences and release readiness

- **Third-party licence inventory:** review Python and JavaScript dependencies, vendored libraries, fonts, icons, images, and Android/native components. Add all required notices before exposing the student-facing licence note.
- **Project code licence:** PwaniNet has no open-source licence selected. Keep the repository marked `UNLICENSED`; do not imply that MIT or any other reuse licence applies.
- **Public pages and links:** implement the approved About and Privacy pages and the short licence notice. Link Privacy from login and Settings → About; link About and licence information where appropriate. Keep the internal documentation index and this issue list unavailable from student-facing navigation.
- **Effective date and changes:** set the policy effective date and decide how material updates will be communicated.
- **Launch feature scope:** confirm direct messaging remains disabled in production; it is frozen until further notice.
