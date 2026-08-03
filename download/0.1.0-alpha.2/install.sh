#!/bin/sh
set -eu

cat >&2 <<'EOF'
StatePort v0.1.0-alpha.2 installation is disabled.

The published candidate has a known packaged web-image defect: two runtime
source trees required by the AppServer were omitted. No successful install
receipt exists, and alpha.2 cannot be accepted or repaired in place.

The signed artifacts remain online for cryptographic inspection. Wait for a
new corrected, rebuilt, re-signed successor candidate before installing.
See: https://lennertvhoy.github.io/StatePort-Site/download/
EOF
exit 2
