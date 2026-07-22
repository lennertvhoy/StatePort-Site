# StatePort Site

The public product story, documentation, tutorials, prototype evidence, and
release-status home for StatePort.

Live site: <https://lennertvhoy.github.io/StatePort-Site/>

This repository keeps the public website separate from the current private
implementation repository. The release ledger is the source for availability
until a public source release exists.

## Architecture

The site intentionally uses static HTML, CSS, and small progressive-enhancement
JavaScript. There is no framework runtime, tracking script, remote font, or
client-side data dependency. Core content remains readable without JavaScript.

- `assets/site.css` contains the established visual system.
- `assets/site-enhancements.css` contains additive product, documentation,
  responsive, print, and accessibility refinements.
- `assets/site.js` adds resilient navigation, breadcrumbs, documentation
  grouping, page tables of contents, previous/next links, code copy, and the
  documentation filter.
- `releases/` is the authoritative public availability boundary.
- `SITE_AUDIT.md` records the critical UX/product audit, decisions, risks, and
  deferred work.

## Run locally

```bash
python3 -m http.server 4173
```

Then visit <http://127.0.0.1:4173>.

## Validate

```bash
python3 scripts/validate_repo.py
python3 scripts/check_site_quality.py
```

The first script protects repository shape, local references, workflow
integrity, contrast, and the public/private source boundary. The second checks
page structure, entry-point metadata, image hints, captions, fragment links,
the sitemap and manifest, tracking absence, and static asset budgets.

## Publishing

Pushes to `main` invoke `.github/workflows/deploy-pages.yml`. The workflow uses
the GitHub Pages custom-workflow flow; Pages must be enabled for the repository.
Pull requests run the non-deploying validation workflow.
