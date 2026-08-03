# StatePort v0.1.0-alpha.2 — Known Limitations

This document is part of the signed release index. It states what this
candidate does not do, does not claim, or has not proven.

## Scope and platform

- Linux AMD64 only; Ubuntu 24.04 is the validated host baseline.
- Rootless Podman with cgroup v2 is required; Docker, rootful Podman,
  and cgroup v1 are refused, not supported.
- Single-user, single-host operation. No multi-user, tenancy, or hosted
  offering exists.
- Services bind loopback only; no public ports are opened by default.
- The API refuses non-loopback binds unless the operator explicitly passes
  `--allow-public-bind`; inside the packaged container network that flag is
  required for the API to listen on the container interface, but it still
  never publishes a host port by itself. Host exposure remains a separate,
  explicit operator action.

## Update authority

- In-place update is implemented for this alpha through the updater's
  pinned-public-key trust line: the installer pins the release trust root
  out of band and persists it durably, `stateport update`
  `check`/`plan`/`authorize`/`apply`/`rollback`/`reconcile` verify every
  successor against that durable trust root (never against the candidate
  artifact itself), and apply is health-gated with automatic rollback and
  predecessor retention. Update application additionally requires an exact
  authorization bundle produced by `authorize`.
- Trust-root rotation is an operator act through the same out-of-band
  pinning path as installation. A release artifact can never rotate the
  trust root in band; a successor signed by a different key is refused as
  an untrusted signer.
- The alpha default update policy is `notify`; automatic application is
  opt-in and remains health-gated with rollback.
- The installer ships guided `--uninstall` (stops and removes services
  and Quadlet files, preserves all data volumes and the state root,
  receipted) and `--purge` (also removes the recorded volumes and state
  root; refuses unless the exact installed identity ID is confirmed).
  Purge does not remove podman networks created by the installation's
  `.network` Quadlets; remove them explicitly after purge if desired.
  Reinstalling over preserved data converges and restores the previous
  state.

## Supply chain

- This is a private engineering candidate: signatures are not uploaded
  to a public transparency log (`not-uploaded-private-candidate`).
  Trust is the pinned alpha release public key and its recorded
  fingerprint.
- Vulnerability scan dispositions are time-bounded; the release index
  carries the scan and database timestamps and refuses stale evidence.

## Infrastructure

- Azure deployment is not applied and not proven. Terraform code and
  offline validation exist; the live apply remains owner-gated with an
  exact plan, cost bound, and TTL.
- No production deployment of any kind has been performed or approved.

## Product surface

- Deployment governance for arbitrary projects is a host-CLI capability
  (`stateport deploy …` from a source checkout). No reviewed catalog
  application declares the Deployments workbench tool in this candidate, so
  the browser does not expose deployment plan/apply/update/rollback for
  unrelated projects. StatePort's own services are governed through the
  Compose/Quadlet install and the updater.
- No preview gateway exists in this candidate. Deployments bind loopback
  host ports directly; there is no browser-mediated preview proxy, no
  capsule route management, and no remote-target preview.
- Browser authority management is the Approvals queue, policy detail, and
  receipts. The Guarded/Balanced/Delegated/Custom profile picker and the
  five-mode grant editor exist only in the mock adapter, not in the shipped
  candidate; standing grants are managed through the private authority
  store and CLI.
- Same-UID local attackers are out of scope for this alpha: authority
  receipts and the audit chain use keyless hashes that detect accidental
  corruption, not adversarial same-UID rewrite or deletion
  (`docs/THREAT_MODEL.md` T12, backlog `BL-INTEGRITY-HMAC-001`).

## Evidence and review

- Human acceptance is pending; this candidate has no human-acceptance
  claim.
- Reviews are internal multi-agent reviews with independence not
  established; no independent security audit exists.
- Test suites that exercise Podman and port fixtures must not run
  concurrently with the image build on the same host (shared store and
  port 5000); this is a test-environment rule, not a product defect.
