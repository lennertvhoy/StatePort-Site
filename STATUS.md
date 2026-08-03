# StatePort Site status

**Updated At:** 2026-08-03
**Execution Mode:** operating
**Project State:** public_alpha_2_candidate_published
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.2` is publicly downloadable from the versioned download
  directory. The signed release index, release-index bundle, public key,
  installer, updater wheel, source archive, release notes, limitations,
  Compose definition, image signatures, and export evidence are published.
- The public release-index file SHA-256 is
  `9cd33eb7d93b5c70bec9f260824ce45877323ec85993a8b2824411e9b2e43000`;
  its signed payload digest is
  `sha256:692f63cdbdfe531aa4d6379d12ad6e98cd408d7343392bf94f5c01abc46af9aa`.
- A one-command bootstrap is published at `download/install.sh`. It downloads
  and verifies the immutable alpha.2 installer, release-index bundle, public
  key, and an exact Cosign binary before invoking the signed installer.
- The alpha.2 signed host target remains **Ubuntu 24.04 AMD64**. This is a
  release-contract and evidence boundary, not an assertion that the container
  workloads fundamentally require Ubuntu. Cross-distribution support requires
  a new signed target and clean-install evidence; alpha.2 is never patched or
  bypassed in place.
- Human acceptance and a clean public-install receipt are pending. Independent
  security review, production qualification, hosted operation, multi-user
  support, ARM64, macOS, and Windows are not claimed.
- Old feature, candidate, and archive branches are historical only. No branch
  other than `main` is active product or release authority.

## Exact next action

Run the public one-command bootstrap on a fresh Ubuntu 24.04 AMD64 machine,
retain the exact install/refusal receipt, and record the owner verdict. Do not
start another candidate, site redesign, media render, or cross-distro release
before that result is known.
