# Diagram text rendering repair — 9 September 2026

Scope: all ten current public whitepaper diagrams. Architecture, narrative,
accessible descriptions, source links, historical candidate, and release bytes
are preserved. No native installed-product qualification claim is made.

## Cause and repair

Live baseline at 9a33916: default workstation Chromium rendered legibly. A controlled
font substitution to installed Noto Sans reproduced text extending beyond fixed
foreignObject boxes in every diagram (9, 6, 11, 5, 7, 4, 8, 8, 3, 3 affected labels
respectively). The original SVG requested a platform-dependent Inter/system font
stack, but boxed its HTML labels using the generation machine's font metrics.
This demonstrates the clipping mechanism; the owner's exact font/browser was not
available and is not claimed reproduced.

Paper theme now uses native SVG text, Arial/Helvetica/sans-serif and 16px labels,
with 16px node padding. Both Mermaid HTML-label settings are disabled. Regenerated
all ten SVGs from unchanged Mermaid source; no generated SVG was manually patched.
Responsive images fit their figure rather than cutting off a branch at phone width.
At 360px the widest diagram scales from 350px to about 310px (roughly 14.2px text);
full-size SVG links retain the natural size. No external fonts or scripts added.

## Verification

`node scripts/check_paper_diagrams.cjs` against a task-owned loopback server at
127.0.0.1:4194 checks each diagram embedded and direct at 360, 768, and 1440px,
JavaScript enabled and disabled: 120 observations. It compares every quoted source
label to rendered text, rejects foreignObjects, checks text bounds against nodes
and the SVG viewport, and repeats geometry after the Noto Sans substitution.
Screenshots include every figure/view and direct SVG, plus font-stress images.
Visual review covers all complete labels, branch nodes, and decision diamonds.

| Figure | Subject | Source text / bounds / visual review |
| --- | --- | --- |
| 1 | Durable state and tools | Passed |
| 2 | Separate owned instances | Passed |
| 3 | Work request path | Passed |
| 4 | Shared permission scope | Passed |
| 5 | Outcome and continuation | Passed |
| 6 | Development and operating uses | Passed |
| 7 | Approval and validation | Passed |
| 8 | Uncertain remote outcome | Passed |
| 9 | Portability questions | Passed |
| 10 | Coherent recovery | Passed |

Reports/screenshots: `output/diagram-clipping-20260909/`. `font-before.json` and
`font-before-*.png` retain the controlled failure. `local/report.json` records
local checks; `live/report.json` is the same check against anonymous public Pages
when publication completes. `public.json` records exact byte comparison for HTML,
CSS, all ten SVGs, and all ten Mermaid sources. These reports describe their own
observed environment; local success is not a claim of successful publication.

Repository validation, 31-page site quality checks, and 30 unit tests passed.
The outcome gate remains exit 1 because the independent full-product primary is
blocked on Alpha.16 signature/package access and native WSL2 evidence.

## Continuation and coordination

Continue with bounded diagram repair/publication: static reading is an unchanged
acceptance criterion, the measured font mismatch supplies new evidence, and native
qualification cannot resolve SVG clipping. Publication follows passing local
integration through the existing command-bound guard and single governor slot;
then verify served bytes and repeat the browser check. No installer rerun is
justified by these asset-only changes.

Reviewed the 2026-09-06 upgrade guidance and reference continuation rules. Existing
instructions contain the refresh and the gate is byte-identical to the reference.
Retain migration notices: its required native journey is still blocked, not newly
run or passed. Next prerequisite is a qualified additive installer successor and
an available genuine native Windows/WSL2 test target.
