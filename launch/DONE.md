> Superseded on 2026-10-01: this file records the Alpha.20 launch of 2026-09-30 and is kept as history. The one-line route now installs Alpha.21 (installer SHA-256 `5fc574f25072f1c801cd40a098126eb230934e8af4f18f8e5c1518955d0cc9e0`); what the pages say now is in `README.md`. Superseded again on 2026-10-07 (branch `copy/alpha23`): the route switches to Alpha.23 (installer SHA-256 `f14c53e5ce596cd81b234f70b23d755aacc9eac9bd2adf3644a251807090d0c8`). Superseded again on 2026-10-03 (branch `copy/alpha22`): the route is prepared to install Alpha.22 (installer SHA-256 `60db0ca4dc590eeadd328c34bd20e1cfe202ac00f066289272fa12229d03db43`).

# Launch DONE — 2026-09-30

All four brief items are met. The only step left is the owner clicking "Post" (steps in `launch/README.md`).

1. **Live site tells one honest Alpha.20 story** — deployed to `origin/main` (fast-forward `dea0d0a..e24de36`, branch `launch/linkedin-20260930` pushed first). Verified live anonymously:
   - Home: "Alpha.20: installs on Windows 11 + WSL2 from one command (verified five times on Windows 11 VMs). Early alpha — known limits below." (grep-confirmed on the live page)
   - Download: exact one-line command, target requirements, displayed installer SHA-256, issues link.
   - Releases: measured installer row, known-limits table, issues link (added), review date 30 September 2026.
   - Known limits stated plainly: reboot survival, templates, uninstall/reinstall, full UI inventory, efficiency not yet measured; "early alpha" wording retained everywhere.
2. **LinkedIn kit in `launch/`** — `post-en.md` (190 words, first person, hook: state that survives the conversation), `post-nl.md` (198 words, Dutch), `first-comment.md` (EN+NL: links + feedback wanted), `screenshots/` (4 real product-UI captures from the site), `demo/stateport-demo-19s.mp4` (24.4 s, 5.3 MB, real product UI, trimmed from the published 33 s overview to cut the outdated Alpha.3 status card). No guest capture needed, so no CAPTURE-REQUEST.md.
3. **`launch/README.md`** — one page: what was published, verification commands, the owner's posting steps (copy text, attach video, post, pin first comment, glance at the link preview).
4. **Anonymous verification (all green, 2026-09-30 ~13:40 UTC)** —
   - `curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sha256sum` → `b83e8376776cd663b6a0aa8098ddde489f0125e033d70e8b1421fb04d1cb8916`, identical to the digest displayed on the live download page.
   - Post/comment links all 200: `/`, `/download/`, `/releases/`, `/download/install.sh`, `github.com/lennertvhoy/StatePort-Site/issues`.

Validation before push (clean clone of the branch, recorded manifest modes applied mode-only): `scripts/validate_repo.py` OK; `scripts/check_site_quality.py` OK (34 pages); 63 unit tests OK; `scripts/projectstate_gate.py` exit 1 (honest: full journey — reboot, uninstall/reinstall, human acceptance — not closed; nothing on the site overclaims it).

Notes: the Windows reboot qualification (`~/.local/state/stateport/alpha20-publish/gov-reboot-1259/`) still had no result at publication; the site keeps saying "not yet measured". The canonical checkout `~/Projects/StatePort-Site` is on an unrelated in-flight branch with local changes — untouched, to be levelled with `origin/main` when that work closes. This session could not visually inspect images (no image input); the social-card link preview is listed as a 10-second owner glance in `launch/README.md`.
