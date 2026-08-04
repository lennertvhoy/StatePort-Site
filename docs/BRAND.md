# StatePort brand usage

StatePort uses the supplied blue mascot vector as its primary product mark.
The transparent SVG is copied byte-for-byte into the web asset pipeline and
appears in the application shell. The favicon is a separately recorded
small-size cap/eyes/beak derivative because the complete mascot was not
legible at tab size. The white-background source is a reviewed provenance
variant, not a dark-shell asset.

## Product tokens

- Infrastructure navy: `#0B132B`
- Orchestration blue: `#2563EB`
- Active-port cyan: `#22D3EE`
- White: `#FFFFFF`
- Supporting slate: `#94A3B8`
- Success, warning, and critical colors are separate semantic tokens.

The canonical CSS token source is
[`apps/web/src/styles/tokens.css`](../apps/web/src/styles/tokens.css),
with the machine-readable summary in the private-internal
`brand/design-tokens.json`.

## Asset boundary

The source and output hashes are recorded in the private-internal
`brand/source-manifest.json` and
`apps/web/assets/brand/favicon-asset-manifest.json`.
Do not redraw the primary mascot in CSS or derive it with filters. Preserve
its source geometry, viewBox, proportions, and blue fill. Use the transparent
variant on dark surfaces; do not place the white-background variant over the
dark shell.

## Accessibility

Brand color is not used as the only status signal. Focus uses a visible cyan
ring, semantic labels accompany status colors, and reduced-motion and
forced-colors fallbacks are included in the stylesheet.
