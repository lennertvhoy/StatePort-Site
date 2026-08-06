# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-08-06
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA3-PUBLIC-PROOF] Verify the live Pages bootstrap

**Status:** pages_deployed_via_actions_owner_proof_pending

Alpha.3 is published on `main` for the portable
`linux-amd64-rootless-podman-quadlet` target. Ubuntu 24.04 has the
`validated_baseline` receipt and Fedora 44 has the `compatible_unvalidated`
receipt, both bound to release-index digest
`sha256:3353fdb6477fcb5269169177c625205c7737b13c904de0c4f70801d7189f3f38`.
Pages now deploys `main` through the Actions deploy provider on every push,
after the legacy branch-source builder stalled. Run the public URL journey on
the receipted Ubuntu 24.04 host, capture the receipt and seven-image/index
verification, and record that the candidate is published but not
owner-accepted.

**Exit:** Pages passes; the public URL install succeeds with
`supportTier: validated_baseline`, all seven image digests and the signed index
verify under the pinned key fingerprint, and the receipt path plus site commit
are recorded in both evidence worklogs.

## Completed

- Rewrote the public download, release-status, and home pages in plain voice
  with the one-line installer front and center (`/download/`, `/`, and a short
  table on `/releases/`). `install.sh` and all signed artifacts under
  `download/0.1.0-alpha.2/` and `download/0.1.0-alpha.3/` were not changed;
  validators and the install-script syntax check pass.
- Published the immutable alpha.3 artifact tree and capability-gated bootstrap.
- Preserved the alpha.2 signed files and fail-closed bootstrap unchanged.
- Updated public release, download, limitation, update, and security copy to
  distinguish published, clean-installed, human-accepted, independently
  reviewed, and production-qualified states.
