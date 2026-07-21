# StatePort Site status

**Updated At:** 2026-07-21
**Execution Mode:** operating
**Project State:** published_initial_site_with_expanded_package_and_local_release_readiness_remediation_pending_review_merge_and_deployment
**Repository:** https://github.com/lennertvhoy/StatePort-Site
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- A static, accessible public site is implemented locally with a homepage,
  documentation index, introductory guide, tutorial path, release ledger,
  404 page, sitemap, and GitHub Pages workflow.
- The release ledger is the public source for availability. It does not link
  to the private implementation repository.
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
- The expanded public documentation package includes foundations, model,
  lifecycle, governance, security and privacy, hosts and portability, evidence
  and roadmap, reference and FAQ, and a receipt-reading tutorial.
- A captioned 83-second local prototype walkthrough, four fixture-based UI
  screenshots, a public whitepaper reader plus source Markdown, an Agent Kits
  roadmap, and a LinkedIn post draft are complete on
  `agent/public-showcase` and pushed as draft PR
  [`#1`](https://github.com/lennertvhoy/StatePort-Site/pull/1). `python3
  scripts/validate_repo.py` passes; fresh desktop and mobile browser review of
  the homepage, media, Agent Kits route, and release ledger found no console
  errors.
- The public voice now leads with work, ownership, and the product surface.
  Availability is kept in one quiet release ledger rather than repeated across
  every page; technical documentation retains the distinctions it needs.
- A local release-readiness remediation adds a capability-based platform-support
  contract and first clean-install user story, plus a scoped documentation-button
  contrast repair. The static gate now verifies the CSS override, white-on-dark
  WCAG contrast, and visible keyboard focus treatment. Desktop and mobile
  loopback review passed with no console errors; the mobile matrix scrolls
  inside its region without widening the document.

## What is not proven

- Public source availability, a licensed release, downloads, or an installation
  path for visitors.
- Human acceptance of the copy, visual design, or information architecture.
- Merge, Pages deployment, and public-runtime verification of the expanded
  documentation, media, paper, roadmap, post-draft package, or the local
  release-readiness remediation.

## Next action

Review the local remediation alongside the expanded package. Only after review,
submit its exact commit to draft PR #1 and verify the matching remote checks;
merge, deployment, and public-runtime verification remain separate steps. Keep
release/download content tied to a public source release and its evidence.
