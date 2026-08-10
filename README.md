# StatePort Site

The public product story, documentation, tutorials, prototype evidence, and
release-status home for StatePort.

Live site: <https://lennertvhoy.github.io/StatePort-Site/>

This repository keeps the public website separate from the current private
implementation repository. The release ledger is the source for availability
and release evidence; the curated alpha.3 source archive is public while the
canonical development Git remains private.

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

GitHub Pages serves the site from the `main` branch through GitHub's managed
legacy Pages build: a push to `main` is picked up and served directly.
`.github/workflows/deploy-pages.yml` is a manual-only custom workflow and is
not the deployment provider. Pull requests run the non-deploying validation
workflow.

## License

This repository has its own licensing boundary, independent of the StatePort
implementation repository: site source code under MIT, written content and
media under CC BY 4.0, and brand assets (name, shell mascot, derivatives)
all rights reserved. See `LICENSE` for the boundary, `NOTICE` for the asset
inventory and attribution review, and `LICENSES/` for the full texts. The
licence choice is recorded locally and takes public effect only when the
owner accepts and publishes it.
