#!/usr/bin/env python3
"""Render the digest-pinned Alpha.6 bootstrap transport command."""

from __future__ import annotations

import argparse
import shlex


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.6/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "ffc144d39502fde804c75f2dbf9994c25bd1f8a2cf3af7fbfb1e9a8352228ee9"
VERSIONED_BOOTSTRAP_SIZE = 18_084
BOOTSTRAP_URL = "https://lennertvhoy.github.io/StatePort-Site/download/install.sh"
BOOTSTRAP_SHA256 = "ffc144d39502fde804c75f2dbf9994c25bd1f8a2cf3af7fbfb1e9a8352228ee9"
BOOTSTRAP_SIZE = 18_084
PREFLIGHT_SUCCESS = (
    "StatePort Alpha.6 materialization preflight passed: target, pinned helper transport, "
    "and absent-parent creation order verified; packages, root files, images, and installer "
    "were not changed or executed."
)
MANIFEST_DIGESTS = {
    "stateport-api": "202a1a5a61a43633ffd32bef46c55654dec97f4b066c531a8cbd0b072c3a7eab",
    "stateport-dev-workspace": "7cbb7d90b17afb1557763d5e8ccb05b310443ca25fa22e744672798a0766192d",
    "stateport-execution-host": "374ef439641472465f12c37cefcf1914df800888ff84454517c6ad26d395bb2a",
    "stateport-playwright": "e7a8c1dd4a7798bb8a9bee4068e845e41b845f52682338b0370d1e566c813db1",
    "stateport-runner": "604a93259b32a46849ea4ad098ae5aa379abf199a32c0f31b2f832b36af64795",
    "stateport-web": "945c09cced090aa67e773445e7580a232b9f2174742bddc9dc8fd264de774375",
    "stateport-worker": "f6e161c833ba1aba4173df5088f3cbb0d1a30032ae083c64dc525a1697a10f1b",
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
