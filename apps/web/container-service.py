#!/usr/bin/env python3
"""Start the canonical StatePort AppServer inside the web OCI image.

This wrapper only makes the repository's source-tree packages importable. It
does not implement HTTP, proxy, or static-serving behavior; the AppServer
remains the sole same-origin authority and the thin service entry adds durable
assistant events, refresh projection, per-work cancellation, and redelivery.
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]

for parent in (ROOT / "packages", ROOT / "apps"):
    for source in sorted(parent.glob("*/src")):
        if source.is_dir():
            sys.path.insert(0, str(source))

from stateport_persistent_app.service_resilient_entry import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
