#!/bin/sh
set -eu
printf '%s\n' 'StatePort Alpha.10 was rejected after the stock Ubuntu 24.04 public install received Podman 4.9.3 below the required floor. Installation is disabled; do not manually upgrade Podman to continue this candidate. Alpha.11 is being prepared.' >&2
exit 1
