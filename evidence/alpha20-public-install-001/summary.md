# Alpha.20 public install — measured on a genuine Windows 11 host, 2026-09-30

Current-view evidence entry for the Alpha.20 signed candidate; the
`alpha17-public-install-001` and `alpha16-public-install-001` entries remain retained
history for their candidates.

## Primary journey

Environment: genuine Windows 11 Pro 25H2 (10.0.26200.8037) KVM guest on the
qualification workstation (not bare metal), WSL2 2.7.14, stock Ubuntu 24.04, anonymous
public route, fresh overlay per run.

1. **One-line install (twice, identical public bytes)** — the documented command against
   `download/0.1.0-alpha.20/bootstrap.sh` completed with `StatePort is installed and
   healthy`, driver exit 0 (1248 s), install receipt `result: succeeded`,
   `healthy: true`, `localUrl http://127.0.0.1:18012/`,
   `activationTarget stateport-accepted.target`; execution host provisioned rootless,
   protocol-healthy, no privilege escalation.
2. **Session-close survival with the shipped keep-alive activated** — after an
   interactive Windows logon (performed by the qualification agent through the VM
   console; no autologon premise; provenance recorded in the product repository's
   evidence), the installed `StatePortKeepAlive` task (ONLOGON,
   `wsl.exe -d Ubuntu-24.04 --exec sleep infinity`) fired and held the WSL environment;
   the linger-enabled control user restarted the accepted target; all containers
   reported healthy ~3 minutes after logon; and with the task's session the only WSL
   session, the installed product served HTTP continuously (180 s relayed responses
   plus 120 s clean 200 s).

Not yet run on this guest: Windows reboot survival, the human-logon form of the
keep-alive activation, template lifecycle, UI inventory, efficiency legs, uninstall and
reinstall. The overall journey therefore remains unpassed; these two legs are measured
green.

## Secondary checks

- `scripts/test_containment.py`: passing after this flip (mode alignment plus the
  current-bootstrap expectations updated to the Alpha.20 bytes).
- `scripts/validate_repo.py`: passing after this flip (status text, predecessor pins,
  and the mutable-route bindings updated to the Alpha.20 truth).
- All seven pinned image-manifest digests in `download/install.sh` match the served
  `download/alpha20-manifests/*.json` bytes; the mutable installer is byte-identical to
  the versioned `0.1.0-alpha.20/bootstrap.sh` that the measured installs used.

## Artifacts

Product repository `evidence/one-line-release-001/native-win11-wsl2-20260928/`:
`alpha20-run-summary-20260930.md` (journey narrative and provenance) and
`alpha20-run/` (install receipt, keep-alive queries before/after logon, task list,
both sampling series, console capture).

## Limitations

- The logon that activated the keep-alive was agent-driven through the VM console; a
  human logon was not performed, and the site status text does not claim one.
- Windows reboot survival is explicitly not yet measured; the status text says so.
- The measurement host is a KVM guest, truthfully recorded as such everywhere.
