# StatePort Site status

**Updated At:** 2026-07-21
**Execution Mode:** operating
**Project State:** published_initial_site
**Repository:** https://github.com/lennertvhoy/StatePort-Site
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- A static, accessible public site is implemented locally with a homepage,
  documentation index, introductory guide, tutorial path, release ledger,
  404 page, sitemap, and GitHub Pages workflow.
- The site deliberately states that there is no public StatePort release,
  installer, or download at this time. It does not link to the private
  implementation repository.
- The StatePort shell mascot was copied byte-for-byte from the accepted shell
  asset; its provenance and hashes are recorded in `PROJECT_DNA.yaml`.
- `python3 scripts/validate_repo.py` passes. It verifies StateSpec state-file
  consistency, required public routes, local links/assets, the Pages workflow,
  and the no-private-source-link boundary.
- Desktop and mobile browser review completed locally against a loopback static
  server. The homepage, documentation, release page, responsive navigation,
  and release-status copy rendered without console errors.
- GitHub repository `lennertvhoy/StatePort-Site` is public. The initial
  public-site content commit is
  `d4522dbee2a39d1f2c3c64766ac222b92ed17332`.
- GitHub Pages is configured for a custom workflow. Workflow-dispatch run
  `29853702366` successfully deployed that exact commit, and the public URL
  returned HTTP 200 and rendered correctly in a browser with no console errors.

## What is not proven

- Public source availability, a licensed release, binary downloads, or an
  installation path for visitors.
- Human acceptance of the copy, visual design, or information architecture.

## Next action

Keep release/download content unchanged until a public source release and its
evidence exist. Review the initial public site for human acceptance separately.
