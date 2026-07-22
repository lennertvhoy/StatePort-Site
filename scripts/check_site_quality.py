#!/usr/bin/env python3
"""Run the deterministic site quality checks used by the draft-PR workflow."""

from __future__ import annotations

from validate_repo import (
    validate_documentation_button_accessibility,
    validate_local_references,
)


def main() -> None:
    validate_local_references()
    validate_documentation_button_accessibility()
    print("StatePort Site local links and contrast: OK")


if __name__ == "__main__":
    main()
