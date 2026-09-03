# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-09-03
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-ALPHA11-PODMAN-CLEAN-INSTALL] Owner public-path test of published Alpha.12

**Status:** Alpha.12 is published, signed, install-enabled, and presented on
the site as the current public-test candidate. The owner public-path test
first refused in the immutable installer package preflight because the
bootstrap had not staged signature bundles into their digest slots; after
that repair it refused again because a leftover non-installed dpkg row made
`python3-venv` report a malformed identity and the bundle's `python3.12-venv`
dependency was unsatisfied. The mutable route now carries both transport
repairs over the unchanged versioned bootstrap. Alpha.11 is superseded and
install-disabled (retained as history); Alpha.10 remains rejected and
install-disabled.

**Decision:** Alpha.12 remains the current public-test candidate; the site
release truth and validators bind the immutable versioned bootstrap plus the
repaired mutable route. The owner public-path install test and human verdict
remain.

**Exit:** Owner clean-install receipt on a real Windows 11 + WSL2 + Ubuntu
24.04 host after the mutable-route repairs, then the human verdict. Human
acceptance remains separate.
