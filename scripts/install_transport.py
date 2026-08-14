#!/usr/bin/env python3
"""Render the digest-pinned Alpha.5 bootstrap transport command."""

from __future__ import annotations

import argparse
import shlex


BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.5/install.sh"
)
BOOTSTRAP_SHA256 = "104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a"
BOOTSTRAP_SIZE = 8_971


def render_install_command(*, execute: bool = False, shell: str = "/bin/sh") -> str:
    """Return a complete-download command; execution is explicit and opt-in."""

    quoted_shell = shlex.quote(shell)
    action = (
        f'{quoted_shell} "$tmp"'
        if execute
        else "printf '%s\\n' 'Alpha.5 bootstrap transport verified; installer was not executed.'"
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
        help="render the held-back install form instead of the non-executing probe",
    )
    args = parser.parse_args()
    print(render_install_command(execute=args.execute))


if __name__ == "__main__":
    main()
