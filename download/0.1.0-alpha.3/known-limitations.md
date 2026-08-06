# StatePort v0.1.0-alpha.3 Known Limitations

- Linux AMD64 only; Ubuntu 24.04 is the validated baseline today.
- Rootless Podman with cgroup v2 is required; Docker, rootful Podman, and
  cgroup v1 are refused.
- This is single-user, single-host alpha software with loopback-only service
  exposure by default.
- Fedora 44 and additional distributions are not yet clean-install accepted.
- The candidate has not received human acceptance, independent security review,
  or production qualification.
- Azure deployment is not applied or production-proven.
- Private candidate signatures are not uploaded to a public transparency log.
