# StatePort Site

The public documentation, tutorials, and release-status home for StatePort.

Live site: <https://lennertvhoy.github.io/StatePort-Site/>

This repository keeps the public website separate from the current private
implementation repository. The release ledger is the source for availability
until a public source release exists.

## Run locally

```bash
python3 -m http.server 4173
```

Then visit <http://127.0.0.1:4173>.

## Validate

```bash
python3 scripts/validate_repo.py
```

## Publishing

Pushes to `main` invoke `.github/workflows/deploy-pages.yml`. The workflow uses
the GitHub Pages custom-workflow flow; Pages must be enabled for the repository
once it exists remotely.
