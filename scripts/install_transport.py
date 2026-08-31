#!/usr/bin/env python3
"""Bind immutable Alpha.10 bytes and its exact fail-closed mutable route."""

from __future__ import annotations

import sys


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.10/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
VERSIONED_BOOTSTRAP_SIZE = 17_774
FAIL_CLOSED_MESSAGE = (
    "StatePort Alpha.10 was rejected after the stock Ubuntu 24.04 public install received "
    "Podman 4.9.3 below the required floor. Installation is disabled; do not manually "
    "upgrade Podman to continue this candidate. Alpha.11 is being prepared."
)
FAIL_CLOSED_BOOTSTRAP = (
    "#!/bin/sh\n"
    "set -eu\n"
    f"printf '%s\\n' '{FAIL_CLOSED_MESSAGE}' >&2\n"
    "exit 1\n"
).encode("utf-8")
MUTABLE_BOOTSTRAP_SHA256 = "47bcd413b87a45713da7f23c43d35882bc4eacc55f3aaf82e6a6732d6220665f"
MUTABLE_BOOTSTRAP_SIZE = 282
MANIFEST_DIGESTS = {
    "stateport-api": "bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895",
    "stateport-dev-workspace": "7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0",
    "stateport-execution-host": "fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7",
    "stateport-playwright": "c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59",
    "stateport-runner": "0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160",
    "stateport-web": "6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704",
    "stateport-worker": "46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23",
}


def main() -> None:
    print("Alpha.10 installation is disabled; no install command is available.", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
