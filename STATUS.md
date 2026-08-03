# StatePort Site status

**Updated At:** 2026-08-03
**Execution Mode:** operating
**Project State:** alpha2_published_known_defect_installation_disabled
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.2` remains publicly available as immutable signed material for
  cryptographic inspection. Its signed payload digest is
  `sha256:692f63cdbdfe531aa4d6379d12ad6e98cd408d7343392bf94f5c01abc46af9aa`.
- Alpha.2 is known defective and has no successful install receipt. Its packaged
  web image omitted the updater and preview-gateway source trees required by
  the AppServer runtime import chain.
- The public download page is an erratum, not an install invitation. Both the
  unversioned and alpha.2 versioned bootstrap paths refuse immediately and
  direct visitors to the defect notice.
- Signed alpha.2 artifacts remain byte-identical and inspectable. The site does
  not rewrite, relabel, or imply that the candidate was repaired in place.
- A corrected implementation-source change exists, but no successor image,
  supply-chain evidence, signed index, public download, clean-install receipt,
  restart/reread proof, or human acceptance is published.
- The alpha.2 signed target remains Ubuntu 24.04 AMD64. The Fedora 44 run was an
  unsupported-host diagnostic investigation and provides no support claim.
- Independent security review, production qualification, hosted operation,
  multi-user support, ARM64, macOS, Windows, and cross-distribution acceptance
  are not claimed.
- Old feature, candidate, and archive branches are historical only. `main` is
  the sole public-site authority.

## Exact next action

Keep installation disabled until a corrected successor is published with a
fresh signed index and clean-install evidence. When that exists, add a new
versioned bootstrap instead of changing alpha.2, validate the complete site,
and record the exact successor status in the release ledger.

Earlier records remain in Git history and the repository’s state archives.
