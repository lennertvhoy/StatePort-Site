# Known limitations

StatePort 0.1.0-alpha.17 targets Ubuntu 24.04 running under WSL2 on Windows 11. WSL1 is refused with `wsl1_substrate_unsupported` before provisioning-plan emission, install-state creation, receipt creation, or host mutation. Native Linux remains a separate signed target and does not inherit WSL2 qualification.

Windows 11, WSL2, and Ubuntu identities remain evidence dimensions rather than substitutes for the required runtime capabilities. WSL2 is reported as `compatible_unvalidated` until a clean-install acceptance receipt exists. Human acceptance, independent security review, stability, and production qualification are not established.

Provider login is owned by Codex in a dedicated private home outside StatePort application backups. Uninstall and purge preserve that login; use Codex logout in the accepted runtime before removal if sign-out is wanted. Older installations must provision the signed successor provider directory before update; the updater refuses a missing or unsafe directory before stopping the predecessor. A real provider request and installed upgrade/recovery still require their own evidence.
