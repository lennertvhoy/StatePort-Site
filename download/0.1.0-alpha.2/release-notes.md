# StatePort v0.1.0-alpha.2 — Release Notes

StatePort runs durable, user-owned AI applications whose state survives
sessions and whose changes remain reviewable and undoable. This alpha
candidate installs the Stateware platform with the StudyState application,
the governed local rootless-Podman deployment fabric, and the signed
release/update supply chain.

Exact candidate version: `0.1.0-alpha.2`. Only the `alpha` channel carries
this candidate; no `stable` release exists, so do not pass
`--channel stable` to the installer.

## What is in this candidate

- **StudyState end to end**: Start, Pause, Resume, Redirect, reflection,
  exact review, apply, restart persistence, and visible Undo with exact
  restoration, backed by canonical state and receipts. In this candidate
  StudyState executes through the bundled **synthetic executor** — a
  deterministic, model-free execution host. Model-backed execution requires
  a separately authenticated execution host (for example Codex CLI or a
  direct API adapter) and is not part of the no-checkout install proof.
- **Application-first StatePort frontend**: learner-first Focus surface,
  the Approvals queue with policy detail and exact receipts, catalog and
  instance management, backup/recovery surface, and settings. Browser
  authority management is the Approvals queue and receipts; the
  Guarded/Balanced/Delegated/Custom profile picker exists only in the mock
  adapter, and standing grants are managed through the private authority
  store and CLI.
- **Governed deployment fabric (host CLI)**: local rootless-Podman inspect,
  plan, approval, apply, health, update, failed-update rollback,
  data-preserving remove, and explicit purge, with exact receipts, via
  `stateport deploy …` from a source checkout. The browser does not expose
  deployment plan/apply for unrelated projects in this candidate, and no
  preview gateway exists — deployments bind loopback host ports directly.
- **Signed release supply chain**: digest-bound OCI images, signed
  `stateport.release-index/v1`, SPDX SBOMs, Grype scan dispositions,
  pinned-public-key Cosign signatures, and a no-checkout installer.
- **Updater**: the full in-place update line — `status`, `policy`,
  `check`, `plan`, `authorize`, `apply`, `rollback`, and `reconcile` —
  driven through the `stateport-update` wrapper the installer writes.
  Every successor is verified against the durable, out-of-band pinned
  trust root recorded at install time; apply requires an exact
  authorization bundle, is health-gated, and rolls back automatically on
  an unhealthy successor with the predecessor retained. Trust-root
  rotation is an operator act through the same out-of-band pinning path;
  a release artifact can never rotate trust in band. Alpha default
  policy: `notify`.
- **Guided uninstall and purge**: the installer's `--uninstall` mode
  stops and removes the services and Quadlet files while preserving all
  data volumes and the state root (reinstall over preserved data
  converges and restores previous state); `--purge` additionally removes
  the recorded volumes and state root, refusing unless the exact
  installed identity ID is confirmed. Every removal touches only
  resources from the durable installation record and is receipted.

## Installation

Linux AMD64, Ubuntu 24.04, rootless Podman 4.9.3 or newer, cgroup v2.
No source checkout is required: the installer verifies its own checksum
and signature, fetches and verifies the signed release index on the
`alpha` channel, pulls the exact digest-bound images, installs the Quadlet
units, starts the services, verifies health and runtime identity, and
records an install receipt.

## Trust model

The release index and image set are signed with the pinned StatePort
alpha release key (key id `stateport-alpha-release-2026-08`). Signatures
for this private candidate are not uploaded to a public transparency
log; verification uses the pinned public key and recorded key
fingerprint. Tampering with any signed field, image digest, or artifact
refuses installation.

## Known limitations

See the bundled **Known Limitations** document, which is part of the
signed release index. Headline items: Linux AMD64 only; single-user,
single-host; loopback-only by default; no browser deployment UI or preview
gateway for unrelated projects; synthetic-executor StudyState; purge
leaves the installation's podman networks for explicit removal; Azure
code validated offline but never applied.

## Status

This is an alpha engineering candidate. Human acceptance is pending.
Reviews so far are internal multi-agent reviews; independence is not
established. It is not production-ready, not a hosted service, and not
multi-user.
