# Licensing and Attributions (Internal Working Note)

## PwaniNet code

PwaniNet's own code is **not being released under MIT or another open-source licence at this time**. The npm metadata is set to `UNLICENSED` to avoid implying that the Capacitor package is offered for unrestricted reuse. This does not replace or alter the separate licences of third-party dependencies and assets.

If the project later chooses to be open source, choose a licence deliberately, confirm the operator has authority to license every included work, and inventory any University-owned, contributor-owned, or third-party material first. MIT is permissive: it allows reuse, modification, distribution, sublicensing, and sale subject to preserving the copyright and licence notice. Do not select it by default.

## Third-party software and assets

Each third-party component keeps the terms of its own licence. Before publishing a user-facing licence/attribution page:

- review Python dependencies from `requirements.txt` and JavaScript/Capacitor dependencies from `package-lock.json`;
- preserve notices for vendored libraries under `static/vendor/` and any Android/native components;
- include bundled font licences and attribution requirements (several fonts under `fonts/` include SIL Open Font Licence notices);
- check image, icon, illustration, and media provenance, including any University marks or photographs; and
- verify that required notices are shipped to users in an accessible place such as Settings → About → Licenses.

This inventory is not yet complete and is not a substitute for the individual licence texts. Do not claim that PwaniNet itself is open source based on a dependency's licence.

