# StatePort v0.1.0-alpha.3 Release Notes

This corrected alpha candidate carries the portable Linux capability contract,
the repaired packaged web content, fixed Chrome for Testing payload, and a
fixed `ip-address` npm dependency in the developer workspace image.

The candidate is for Linux AMD64 hosts with Linux kernel support, cgroup v2,
rootless Podman, Quadlet, systemd user services, and subordinate UID/GID
mappings. Ubuntu 24.04 is the validated baseline; Fedora 44 validation remains
mandatory before public release.

This is a private engineering candidate. Human acceptance, clean-install
qualification, independent security review, and production qualification are
pending. Signatures use the pinned private-candidate trust root and are not
uploaded to a transparency log.
