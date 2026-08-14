# Known limitations

Alpha.5 targets Ubuntu 24.04 running under WSL2 on Windows 11. WSL1 is refused with `wsl1_substrate_unsupported` before provisioning-plan emission, install-state creation, receipt creation, or host mutation. Native Linux remains a separate signed target and does not inherit WSL2 qualification.

Windows 11, WSL2, and Ubuntu identities remain evidence dimensions rather than substitutes for the required runtime capabilities. WSL2 is reported as `compatible_unvalidated` until a clean-install acceptance receipt exists. Human acceptance, independent security review, stability, and production qualification are not established.
