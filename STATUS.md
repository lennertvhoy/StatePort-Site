# StatePort Site status

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Project State:** alpha5_install_disabled_materialization_preflight_pending
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.5` is the current signed public-test candidate for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`. Its signed index
  SHA-256 is `4613fcad48ea1a2e7dd4350d61baa333efbc734b1fcba1a1c9ca62994d562b71`
  and signed payload is
  `sha256:e45d5c8ce6843bd0c3155ecd26940ff3dc11c5069a2de796a079708066faf98c`.
- The immutable 33-file Alpha.5 tree is anchored by Site commit
  `eaa1ca6a67844259860917442a95c891d097939f`; its bootstrap remains 8,971
  bytes at SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`.
- The owner reports that the first exact
  Windows 11 + WSL2 + Ubuntu 24.04 AMD64 command installed prerequisites, then
  Dash failed on an unterminated quote before the Python installer ran. No
  receipt exists; this is a failed partial attempt with side effects.
- Completed reviews found a 4,096-byte truncated pipe-to-shell transfer. The
  complete 8,971-byte bootstrap remains valid at SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`;
  the signed payload is not implicated.
- The owner reports the replacement then downloaded all 8,971 bytes, matched the
  pinned SHA-256, and passed target `/bin/sh -n` without executing the installer.
  Only that repaired command is authorized for re-enablement. This is not a
  clean-install receipt or independently captured raw evidence.
- The owner reports the complete bootstrap then refused the five private image
  signatures visible in the transcript because exact local manifest bytes were
  unavailable. The signed inventory contains seven affected private-manifest
  paths. No install receipt exists; the refusal JSON is not copied locally.
- Canonical source commit `256d8761` / tree `e7fb80c5` remains in private
  development Git. Signed public snapshot `6911b7c1` / tree `05ca882f` is
  anonymously resolvable from `lennertvhoy/StatePort-Source`. The curated
  Alpha.5 source archive is public and AGPL/CC-BY classified.
- Alpha.3 remains signed, byte-intact, install-disabled, and historical. Its
  erratum remains public. Alpha.2 remains superseded and install-disabled.
  Neither retained release tree changed.
- Alpha.5 containment content commit
  `636e795230e286fb39470fe695d935266b4ee876` is deployed through Pages build
  `1151605137`, run `31832575567`, and deployment `5912021497`. All 33
  immutable Alpha.5 files and nine mutable containment surfaces match local
  bytes remotely.
- Re-enablement content `c8cd20804bc2307c5c49f1fbed75ea8c59f921ae`
  deployed through build `1151631061`, exact run `31834012760`, and deployment
  `5912274973`. All 16 changed mutable files and all 33 immutable Alpha.5 files
  matched anonymous live bytes. The legacy build endpoint reported the prior
  state SHA; exact run, deployment, and bytes bind the live content.
- Signature-refusal containment `8cae82e5b98b8d4884a18e50660852d2005c4842`
  deployed through build `1151656087`, run `31835252274`, and deployment
  `5912489564`. All 15 changed mutable files and all 33 immutable Alpha.5 files
  matched anonymous live bytes.
- StatePort commit `df2cbb85` locally supplies all seven exact digest-pinned
  manifests through the immutable installer's existing archive seam. No signed
  or versioned Alpha.5 bytes change. Additive commit `b75357d1` supplies the
  non-installing probe mode. The mutable bootstrap is 13,702 bytes at
  SHA-256 `3f1be353c095b6ef08ea78beca8430b0baea13a890abce8aaf74c49d40808f78`;
  publication is remotely verified and no probe result exists.
- Mutable publication `562c9cfdeff85b3449df37b0011d228ab3857e75`
  deployed through build `1151713417`, run `31838288831`, and deployment
  `5913017331`. All 16 changed mutable files, both unchanged minimal public
  pages, and all 33 immutable Alpha.5 files matched anonymous bytes.
- The owner reports the exact Windows 11 + WSL2 + Ubuntu 24.04 probe passed the
  13,702-byte bootstrap, pinned SHA-256, shell syntax, and all seven manifests
  without installer execution. This authorizes the repaired command only.
- Re-enablement `d5491f32cabda022630b0292e4db440d64760c7d` deployed through
  build `1152517815`, run `31871418918`, and deployment `5918210420`; all 15
  changed paths and all 33 immutable Alpha.5 files matched anonymous bytes.
- The continued Lionheart diagnostic encountered an HTTP 503, prepared the
  signed execution-host plan, then failed because `/usr/local/libexec` was
  absent. No install or execution-host receipt exists; installation is disabled.
- StatePort `c441ca7a` supplies explicit bounded atomic downloads, safe helper
  parent creation, and a no-root-write materialization preflight. Its mutable
  17,561-byte render is published; installation remains disabled.
- Mutable publication `c561db2` deployed through build `1152559503`, run
  `31872664883`, and deployment `5918407409`; all ten changed paths and all 33
  immutable Alpha.5 files matched anonymous bytes.

## Exact next action

Await the exact-target non-installing materialization preflight result. Keep
installation disabled.
