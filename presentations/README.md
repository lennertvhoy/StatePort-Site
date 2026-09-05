# StatePort slides maintained through code

Edit `deck.json`, then rebuild. `build.mjs` creates native editable PowerPoint
text boxes and embedded screenshots, plus a standalone HTML presentation with
all assets included. This is a local JavaScript library and CLI workflow; it
uses no hosted API, accounts, presentation subscriptions, or third-party runtime
scripts. Source screenshots come from `../assets/media/` in this repository.

## Build

Use the supplied Codex primary runtime, artifact-tool 2.8.59 / bundle
26.904.11930. The runtime discovery tool is not exposed in this session; the
installed bundle was found at the path below and its runtime.json inspected.
Do not install replacement dependencies into the bundle.

```bash
export RUNTIME_ROOT=/home/ff/.cache/codex-runtimes/codex-primary-runtime
export RUNTIME_NODE_MODULES="$RUNTIME_ROOT/dependencies/node/node_modules"
export PRESENTATIONS_SKILL=/home/ff/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations
"$RUNTIME_ROOT/dependencies/node/bin/node" presentations/build.mjs presentations/deck.json ../.local/stateport-slides-revision-1
```

Use a fresh output directory for each revision: finalization refuses to overwrite
an existing final PPTX. Keep outputs outside the public Site tree. The output
folder contains `stateport-introduction.pptx` and `stateport-introduction.html`.
Open the HTML directly in a browser; viewing needs no build tools or credentials.
The PPTX requires a compatible presentation viewer. DejaVu Sans is the chosen
font; another machine may substitute it if unavailable.

## Present and control

Browser presentation: Previous/Next buttons, arrow keys, Page Up/Down, Home/End,
Show all, and Fullscreen. Without JavaScript all slides remain readable.
Programmatic browser API (zero-based slide index):

```js
window.stateportDeck.go(2);
window.stateportDeck.next();
window.stateportDeck.previous();
window.stateportDeck.index;
window.stateportDeck.count;
```

Fullscreen uses the browser's [Fullscreen API](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API)
and may require a user gesture. The button reports unavailable fullscreen
without preventing presentation. Speaker notes contain evidence limits.

## Edit an existing PowerPoint on a copy

`edit.mjs` is a deliberately narrow title-edit experiment for the tested decks.
It verifies the existing title and resulting title; it does not promise arbitrary
layout editing. Keep its output as a candidate until rendered and compared.

```bash
"$RUNTIME_ROOT/dependencies/node/bin/node" presentations/edit.mjs original.pptx new-candidate.pptx 1 'Old title' 'New title'
```

The file is imported through Artifact Tool and exported as real PPTX. It is not
an image-only conversion. Read the presentation skill before agent authoring;
render the relevant original slide before editing. Render exports with the
bundled viewer, never the owner's desktop LibreOffice:

```bash
"$RUNTIME_ROOT/dependencies/bin/override/soffice" --headless --convert-to pdf --outdir /absolute/private/build /absolute/private/output/deck.pptx
```

## Tested results and limits — 5 September 2026

- New five-slide deck: package/geometry/font/import finalization passed. All five
  slides rendered in bundled LibreOffice and inspected at full size. Native text
  remains editable, screenshots are separate images, and notes survive a title
  edit and re-export. Other text and image bytes matched in that experiment.
- JSON title update and rebuild passed separately. Browser playback passed
  keyboard/buttons/API/fullscreen and all-slide readability without JavaScript.
- Existing deck inventory found six distinct local decks (18–105 slides).
  Original files were not modified or published. One 28-slide StateDD deck was
  copied privately and its first title edited. It opened and retained all other
  slide text, six image byte payloads, slide count, and layout/theme counts.
- **Existing-deck round-trip is lossy.** Render comparison showed missing arrow
  connectors on slides 5, 15 and 24, plus some line/shape differences elsewhere.
  Twenty of 28 rendered thumbnails matched exactly; eight differed including the
  intentional title edit. The shape count changed from 325 to 311, and note-page
  numbering disappeared. Layout/theme counts matching does not prove their
  structure is preserved. The old deck had no substantive speaker notes, so it
  cannot establish note preservation; the new deck supplies that separate test.
- The fixture had no external hyperlink relationships or timing trees. Links,
  animation, audio/video, charts, and SmartArt round-trip remain **not tested**.
  The HTML field-guide link works; native PPTX link behavior is unqualified.
- Actual Microsoft PowerPoint is unavailable here and was **not tested**. The
  bundled LibreOffice result is a separate compatibility claim.

Use source-first rebuilds for this new deck. Do not adopt unrestricted import /
export for valuable existing decks: preserve originals and inspect changes. A
future fidelity test needs representative connector, link, notes, font and motion
fixtures plus actual PowerPoint. Microsoft's [PresentationML structure guide](https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document)
explains why slides, relationships, masters, layouts and notes need separate checks.
