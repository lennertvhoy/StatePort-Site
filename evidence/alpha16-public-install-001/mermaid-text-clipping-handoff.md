# Handoff: fix clipped text in the public whitepaper diagrams

## Owner request and priority

9 September 2026: the owner reports that almost all Mermaid diagrams have cropped
or cut-off text and requests a handoff to fix them. This is a reported public
rendering defect, not an accepted diagram implementation. Do not treat the previous
browser checks or diagram review as proof of label legibility. The user requested
this handoff, not another fix-and-publish run in this turn.

Public paper:
https://lennertvhoy.github.io/StatePort-Site/papers/stateware-whitepaper-public-v1.1.html

Repository: /home/ff/Projects/StatePort-Site, main.
Last published head: 9a33916ce9f3771ead5dc2c569bfac7cdfcdad82.
Current slice: alpha16-public-install-001. Read AGENTS.md, PROJECT.md, STATE.yaml.
Preserve all unrelated dirty coordination files and the Alpha.14 evidence directory.
The native installed-product primary remains blocked; this independent public
rendering fix does not require a new installer qualification run.

## Required outcome

All text in all ten current whitepaper diagrams must be fully visible and readable
in the embedded page and when each SVG is opened directly. Check desktop and mobile,
with JavaScript enabled and disabled. Keep the user's corrected architecture:
ProjectState supports developing projects and operating projects such as StudyState;
StatePort itself was developed using a ProjectState instance. Keep the paper focused
on architecture, not internal development or validation status.

## Relevant implementation

- papers/stateware-whitepaper-public-v1.1.md — canonical narrative and Mermaid blocks.
- papers/stateware-whitepaper-public-v1.1.html — generated article in existing shell.
- scripts/render_paper_diagrams.py — Pandoc/Mermaid renderer.
- config/mermaid-paper-theme.json — current paper-specific 16px theme.
- assets/whitepaper-diagrams.css — embedded figure styling.
- assets/diagrams/src/paper/stateware-whitepaper-public-v1-1-{01..10}.mmd.
- assets/diagrams/paper/stateware-whitepaper-public-v1-1-{01..10}.svg.

Regenerate current paper with:
python3 scripts/render_paper_diagrams.py --paper stateware-whitepaper-public-v1.1

Current publication uses standalone SVGs in img elements, with accessible alt text,
full-size links and Mermaid source links. Preserve those features, fragment aliases,
static operation and local assets. Do not regenerate the historical candidate unless
an evidenced shared defect requires it.

## Diagnose before changing layout

1. Reproduce the owner's report on the live page and direct SVGs, saving screenshots
   of representative cut-off labels. Inspect all ten, not a sample as final proof.
2. Inspect generated SVG text/foreignObject dimensions, node shapes, viewBox, clipping,
   wrapping, line height, fonts and label padding. Distinguish text clipped inside a
   node from the entire diagram being clipped by its figure. Those are different bugs.
3. Compare Mermaid's generation environment with browser display: missing or differing
   fonts, HTML-label foreignObject sizing, CSS inheritance inside an SVG image, and
   text wrapping are hypotheses to verify, not established causes. Consider native SVG
   text labels or explicit line breaks if they remove the measured failure.
4. Fix the rendering source/configuration. Do not patch ten generated SVGs by hand,
   hide labels, reduce font size until unreadable, or enlarge only the outer viewport.
   Regenerate and visually inspect every complete label and node boundary.

## Verification and publication

Prior reports in output/whitepaper-diagrams-20260909/ and committed whitepaper diagram
browser evidence checked asset loading, image dimensions, viewport overflow and links.
Those checks did not establish that text fit inside individual nodes. Treat their
legibility conclusion as superseded by the owner's defect report.

Use isolated headless Chromium, not the owner's desktop. Playwright is available at
/home/ff/Projects/StatePort/apps/web/node_modules/playwright and Chromium at
/usr/bin/chromium. Check at least 360, 768 and 1440px. Save per-diagram screenshots,
inspect the actual text against Mermaid source, and record each diagram's result.
Where possible add a focused meaningful geometry/rendering check for the reproduced
clipping mechanism; image decode/no document overflow alone is insufficient.

Run repository validation, site quality, relevant tests and the outcome gate. The
native primary's existing blocked status must remain explicit in internal evidence.
After all diagram labels pass, publish through the existing command-bound release
guard and governor using the user's standing instruction to make improvements live.
Verify anonymous public bytes for HTML, CSS, SVG and Mermaid sources, then repeat
visual inspection on the served page. Do not claim fixed before that inspection.

## Immediately preceding public-copy correction

The separate owner complaint about internal testing commentary is fixed and live at
9a33916. Homepage/gallery and guide copy were rewritten; the video is now 72 seconds
with matching transcript, captions and chapter links. The internal production footer
was replaced with the sample name. Download/release limitations remain visible.
Nine changed public files matched local bytes anonymously; live browser checks passed
16 page views (360/1440px, JS on/off), and live video playback reached 67.046715s after
seeking to the final chapter (duration 72.041667s). Reports are in
output/public-copy-20260909/public.json and live-browser.json. That success does not
resolve the newly reported diagram clipping.
