#!/usr/bin/env python3
"""Render the digest-pinned Alpha.10 bootstrap transport command."""

from __future__ import annotations

import argparse
import shlex


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.10/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
VERSIONED_BOOTSTRAP_SIZE = 17_774
BOOTSTRAP_URL = "https://lennertvhoy.github.io/StatePort-Site/download/install.sh"
BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
BOOTSTRAP_SIZE = 17_774
PREFLIGHT_SUCCESS = (
    "StatePort Alpha.10 materialization preflight passed: target, pinned helper transport, "
    "and absent-parent creation order verified; packages, root files, images, and installer "
    "were not changed or executed."
)
MANIFEST_DIGESTS = {
    "stateport-api": "bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895",
    "stateport-dev-workspace": "7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0",
    "stateport-execution-host": "fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7",
    "stateport-playwright": "c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59",
    "stateport-runner": "0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160",
    "stateport-web": "6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704",
    "stateport-worker": "46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23",
}


def render_install_command(*, execute: bool = False, shell: str = "/bin/sh") -> str:
    """Return a complete-download command; execution is explicit and opt-in."""

    quoted_shell = shlex.quote(shell)
    action = (
        f'{quoted_shell} "$tmp"'
        if execute
        else f'{quoted_shell} "$tmp" --materialization-preflight'
    )
    return (
        '(umask 077; tmp="$(mktemp)" && '
        'trap \'rm -f "$tmp"\' EXIT HUP INT TERM && '
        "curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "
        f'--output "$tmp" {BOOTSTRAP_URL} && '
        f'test "$(wc -c < "$tmp")" -eq {BOOTSTRAP_SIZE} && '
        f"printf '%s  %s\\n' '{BOOTSTRAP_SHA256}' \"$tmp\" | "
        "sha256sum --check --status - && "
        f'{quoted_shell} -n "$tmp" && {action})'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="render the installer-executing form instead of the non-executing preflight",
    )
    args = parser.parse_args()
    print(render_install_command(execute=args.execute))


if __name__ == "__main__":
    main()
