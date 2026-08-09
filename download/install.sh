#!/bin/sh
printf '%s\n' \
  'StatePort v0.1.0-alpha.3 installation is disabled.' \
  '' \
  'The signed candidate is byte-intact, but its freshness evidence has expired' \
  'and known installer and runtime defects require a successor release.' \
  'No installation command is executed by this disabled bootstrap.' \
  '' \
  'Wait for a corrected, rebuilt, and re-signed successor candidate.' \
  'Erratum: https://lennertvhoy.github.io/StatePort-Site/download/erratum-alpha3.html' >&2
exit 2
