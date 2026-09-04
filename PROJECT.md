# StatePort Site

## User

The primary user is a student or project owner on a fresh Windows 11 AMD64
machine using stock Ubuntu 24.04 under WSL2. They should not need to understand
StatePort's repositories, signing pipeline, container internals, or historical
alpha failures.

## Outcome

The user visits the public StatePort site, finds one accurate getting-started
path, copies one installer command into fresh Ubuntu WSL, and receives a
complete working StatePort. The site then helps them open the product, import
and use ProjectState, StudyState, or any template satisfying the supported
contract, recover from common problems, update, and uninstall.

## Scope

- Clear getting-started, template, troubleshooting, update, uninstall, and
  evidence documentation for the supported environment.
- One anonymous integrity-checked Alpha.16 installer command.
- An additive, signed, immutable Alpha.16 download tree and its exact manifest
  transport files.
- A mutable `download/install.sh` pointer whose bytes and claims agree with the
  Alpha.16 release index.
- Retention of the immutable Alpha.15 predecessor and its exact public evidence.
- Anonymous verification of the deployed Pages bytes and links.
- Preservation of every earlier anchored versioned release tree.

## Non-goals

- Replacing the one-line path with a checkout, Docker Compose, manual package
  repair, or a developer launcher.
- Presenting a frontend build, local file server, staged guest, or passing site
  validator as proof that the installed product works.
- Rewriting an earlier alpha or hiding its historical status.
- Supporting WSL1, native Linux, macOS, ARM64, Docker Desktop, or other
  distributions in this slice.
- Claiming human acceptance, independent review, stability, or production
  qualification without the corresponding evidence.
- Governance files, ledgers, counters, or commit-binding rituals that do not
  reduce a user-visible uncertainty.

## Durable constraints

- Published versioned and signed bytes are immutable and exact provenance is
  preserved from the signed index to the downloaded artifact.
- The public command, version, URL, source identity, images, target, and support
  statement must tell one consistent truth.
- The product must install and run without reading this repository's
  ProjectState coordination files.
- The site remains static, accessible without JavaScript, privacy-preserving,
  locally referenced, and free of third-party runtime code.
- Destructive, privileged, external, and non-idempotent effects fail closed and
  remain attributable.
- Genuine fresh Windows 11 WSL2 evidence is not interchangeable with simulated,
  staged, prepared-host, or local-development evidence.
- The human owns this outcome and acceptance boundaries. Agents may make
  them more observable but may not weaken them.
