# Local Closure Gate

The Local Closure Gate reproduces StatePort's authoritative repository checks
from one exact checkout. It is local validation only: it neither runs nor
claims remote CI.

Run it only from a clean integration, fresh, or container checkout. Keep the
evidence destination outside the repository so evidence generation cannot
change the candidate being tested.

```bash
STATEPORT_BROWSER_STUDYDD_REPOSITORY=/public-safe/StudyDD \
python3 scripts/local_closure_gate.py \
  --environment-label fresh \
  --output-dir /external/evidence/local-closure/fresh
```

The StudyDD value must name a public-safe Git repository that contains the
pinned development-candidate object. The runner passes it to the existing
real-service browser harness but never writes the value to its command record
or logs. The browser harness starts loopback-only disposable services and
cleans up its child processes.

Each required command has a hard timeout. The machine summary records the
exact commit and tree, clean-before/after status, sanitized argv, tool
versions, exit codes, durations, and SHA-256 hashes for sanitized per-command
logs. Missing tools, missing required environment, a dirty worktree, a timed
out command, a failed command, or post-run drift all fail the gate. The
browser suites write to separate per-command artifact roots so one suite
cannot overwrite or inherit another suite's evidence. Raw traces and unknown
artifact formats are discarded; retained text is sanitized and retained
screenshots are hashed. The default plan covers:

- complete pytest, StateSpec schemas, repository validation, compileall, and
  functionality preservation;
- npm's lockfile install, typecheck, lint, unit tests, HTTP production build,
  production/demo isolation, dependency tree, and high-severity audit;
- isolated demo accessibility/responsive Playwright, connected AppServer core
  workflow acceptance, and real-service canonical-source acceptance;
- the repository gitleaks wrapper, `git diff --check`, clean porcelain status,
  and full Git object integrity.

`--dry-run` emits a deliberately failing plan record. It cannot be cited as
validation.

## Human-ready evidence

After active, fresh, and supported container closure records and the focused
review records exist, prepare a small JSON input for
`scripts/build_human_ready_gate.py`. It requires exact functional commit/tree
identities. Every true check needs at least one safe relative artifact path
and its 64-character SHA-256 hash; omitted checks are false.

```bash
python3 scripts/build_human_ready_gate.py \
  --input /external/evidence/human-ready-input.json \
  --output /external/evidence/human_ready_gate.json
```

The command exits nonzero while any check is false. Human acceptance is
permitted only when every required machine check is true. The human session is
then limited to twenty minutes of subjective clarity, control, trust, and
acceptance judgment; it is not a substitute for automated QA.
