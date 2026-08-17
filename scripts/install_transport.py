#!/usr/bin/env python3
"""Render the digest-pinned Alpha.7 bootstrap transport command."""

from __future__ import annotations

import argparse
import shlex


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.7/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "5704e26351357cb8e0f42baabc1d8d09559546e06919967a5d2ae6cdc31f54c5"
VERSIONED_BOOTSTRAP_SIZE = 18_084
BOOTSTRAP_URL = "https://lennertvhoy.github.io/StatePort-Site/download/install.sh"
BOOTSTRAP_SHA256 = "5704e26351357cb8e0f42baabc1d8d09559546e06919967a5d2ae6cdc31f54c5"
BOOTSTRAP_SIZE = 18_084
PREFLIGHT_SUCCESS = (
    "StatePort Alpha.7 materialization preflight passed: target, pinned helper transport, "
    "and absent-parent creation order verified; packages, root files, images, and installer "
    "were not changed or executed."
)
MANIFEST_DIGESTS = {
    "stateport-api": "4c9a99b84f5bb28aeed49735393ba9361a6e060ed52a88b43fe1886d7cb8cd0e",
    "stateport-dev-workspace": "0102c422aa8cf9ba1abb5f708f5ba5280799e9407d9db938f2e771d069524b0f",
    "stateport-execution-host": "e152675e3948602a8885e091b558677b989e2f40083e4a9d554c589273c736ee",
    "stateport-playwright": "214a7b50c8c1f0ba3f20ab3240d0ccce0e8b661f0faf261103717a3eb1bd2508",
    "stateport-runner": "4777530d08ee7b82a91d96ec735a67ae4397ac42aa363203b1c3bfdb0615d6bc",
    "stateport-web": "967657d89a53014a6cb708964d77d8b9ee4913f8414da63a3135696b8b7e05b7",
    "stateport-worker": "be89886a4ee1f766514c66742a366dd4714f60030eb7103bf1075cd3e94d4b02",
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
