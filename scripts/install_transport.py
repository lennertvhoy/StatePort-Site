#!/usr/bin/env python3
"""Render the digest-pinned Alpha.5 bootstrap transport command."""

from __future__ import annotations

import argparse
import shlex


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.5/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a"
VERSIONED_BOOTSTRAP_SIZE = 8_971
BOOTSTRAP_URL = "https://lennertvhoy.github.io/StatePort-Site/download/install.sh"
BOOTSTRAP_SHA256 = "cf8b20d09bc0865e222281cb09a4cece675eff979a84b6cb2e71ba53338a6300"
BOOTSTRAP_SIZE = 17_620
PREFLIGHT_SUCCESS = (
    "StatePort Alpha.5 materialization preflight passed: target, pinned helper transport, "
    "and absent-parent creation order verified; packages, root files, images, and installer "
    "were not changed or executed."
)
MANIFEST_DIGESTS = {
    "stateport-api": "a5c639880195ba6dc57fa9c13378fdf0cdb0361f08cbddea7b7e90f476906af8",
    "stateport-dev-workspace": "1a9eecc2a087620e7139570e09c08b4ce6c17a8369d2b428551809dff3fda886",
    "stateport-execution-host": "02d3ce6d6dfdacc164b947c1c88ebf6c64e0a103b05fbd420454083db589efb2",
    "stateport-playwright": "a5e8bc89bd193bd149dcad3de03366796bcc8f903f019e9e599f928dfaed9096",
    "stateport-runner": "45b5aaf0cd18699a66371ed800683ad5740b491d1442d9c1edd90d87089786ae",
    "stateport-web": "57f625f36c590c1440d70f07a3aa1bee6b31c2a9c942285c897c7934635fccf1",
    "stateport-worker": "ac835bf5449d1f7843734a8cbb9f4a332e9b01e6066f06599798a6964539e551",
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
