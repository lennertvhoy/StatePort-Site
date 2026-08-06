# StatePort Site status

**Updated At:** 2026-08-06
**Execution Mode:** operating
**Project State:** alpha3_published_legacy_pages_public_proof_pending
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
- The public download, release-status, and home pages now lead with the
  one-line installer in plain voice. The command
  `curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.3/install.sh | bash`
  is shown on `/download/` and `/` with a copy control, and `/releases/` is a
  short plain-English status table. `install.sh` and all signed artifacts under
  `download/0.1.0-alpha.2/` and `download/0.1.0-alpha.3/` were not changed.
- Pages now serves the canonical `main` branch directly through the legacy
  branch source (`main:/`), avoiding Actions runner quota and deploy queue
  failures. The former automatic deploy trigger is disabled; its workflow file
  remains only as a validator-required, disabled manual recovery definition.
- `v0.1.0-alpha.2` remains immutable, superseded, known defective, and
  install-disabled for inspection. Its files were not rewritten.
- Human acceptance, independent security review, and production qualification
  are not established. This is published but not owner-accepted.

## Exact next action

After the legacy Pages build serves alpha.3, complete the public-URL
clean-install proof from the live bootstrap on the receipted Ubuntu 24.04
host, capture the receipt and seven-image/index verification summary, then
record the outcome without changing product code or alpha.2 artifacts.
