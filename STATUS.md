# StatePort Site status

**Updated At:** 2026-08-06
**Execution Mode:** operating
**Project State:** alpha3_published_pages_blocked_by_github_actions_incident_public_proof_pending
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.3` is published as a signed alpha candidate for the portable
  `linux-amd64-rootless-podman-quadlet` target.
- The signed release index raw SHA-256 is
  `d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93` and its
  signed payload digest is
  `sha256:2639e29d6ca0a5bd83d07013edb49f22692efaf53a6049234fe6b70810c89166`.
- Ubuntu 24.04 is `validated_baseline`; Fedora 44 is
  `compatible_unvalidated`. Debian and rolling distributions are not claimed.
- The alpha.3 installer evaluates capabilities, refuses non-capable hosts, and
  records the support tier. It makes no all-Linux claim.
- Publication commit is `52b42dd47a11510220f33690075f1b6773f6a889`. Pages run
  `31125217806` is queued with no steps started during GitHub's critical
  `Incident with Actions`; the live URL still serves the predecessor page.
- `v0.1.0-alpha.2` remains immutable, superseded, known defective, and
  install-disabled for inspection. Its files were not rewritten.
- Human acceptance, independent security review, and production qualification
  are not established. This is published but not owner-accepted.

## Exact next action

After GitHub Actions recovers and Pages serves commit `52b42dd`, complete the
public-URL clean-install proof from the live bootstrap on the receipted Ubuntu
24.04 host, capture the receipt and seven-image/index verification summary,
then record the outcome without changing product code or alpha.2 artifacts.
