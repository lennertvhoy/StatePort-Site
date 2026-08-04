# Persistent StudyState local alpha

Use a fresh clone or isolated worktree; inspect `git worktree list` before
testing. This Linux-first, local-single-user alpha needs Python 3.10 or newer;
it needs no provider, cloud resource, root access, or Compose. Read the
[`LOCAL_ALPHA_LIMITATIONS.md`](LOCAL_ALPHA_LIMITATIONS.md) boundary before
using it.

```bash
./stateport setup init
./stateport instance create \
  --source-profile builtin:studydd-local-alpha \
  --destination "$HOME/StatePort/StudyState-AI103" \
  --instance-id studydd-ai103 --name "AI-103 Study" \
  --owner-name "Local Owner" --target-id ai-103
./stateport service start --open
./stateport instance synthetic-run studydd-ai103
./stateport instance backup studydd-ai103
./stateport service stop
./stateport service start --open
```

The instance repository is canonical. Catalog, source cache, runtime files,
dashboard summaries, and run history are disposable management metadata.
Private-state migration from an existing local StudyState instance is planned and
applied separately through the typed `instance import-state-*` commands.

For a public-safe retained demo, use `./stateport demo studydd-local-alpha
--workspace "$HOME/StatePortDemo" --keep`; it refuses an existing workspace
and uses the same governed creation path.

Known limits: synthetic execution is not tutor quality, a narrow opt-in local
Codex provider path exists while other live providers and host adapters are
deferred, browser mutation is limited, encryption and hosted multi-user
operation are not claimed, and remote CI/human acceptance are separate states.
