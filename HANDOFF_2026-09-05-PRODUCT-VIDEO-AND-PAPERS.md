# StatePort Site and Papers — fresh-session handoff

## Latest owner direction

The owner explicitly requested a handoff, with implementation in a **new
session**. This handoff does not implement the following changes.

1. Use the latest local **ProjectState_Template** in the Projects folder and
   integrate it into **StatePort-Papers**, including the relevant paper content,
   not merely repository coordination files.
2. Make the existing mascot **25% smaller** (75% of its current rendered size).
   Preserve the artwork and proportions. This supersedes the earlier request
   to keep its size.
3. Replace the confusing video direction: the owner wants screenshots and
   footage of **StatePort itself**, not a tour of the documentation website.
   The current narrated documentation field guide is **not accepted**.
4. Continue the broader polish of the site and papers: clear content, navigation,
   readable documentation, consistent colors, useful images and diagrams,
   animations and guides. Inspect UI, images and videos for actual visual defects.

The message was dictated. Interpret “Stateboard / state board” as StatePort
unless repository evidence establishes a different intended product. Interpret
“home project state template” as the local ProjectState_Template, while checking
the latest local files before adopting anything. Proceed in English.

## Boundaries

- **`/home/ff/Projects/StatePort` is read-only.** Another agent is working there.
  Do not edit it, run commands that generate files there, or disturb its runtime.
- Editable repositories: `/home/ff/Projects/StatePort-Site` and
  `/home/ff/Projects/StatePort-Papers`. Read each repository's AGENTS.md,
  PROJECT.md, STATE.yaml and current evidence before work.
- Preserve all existing staged and unstaged changes and untracked evidence.
  No reset, clean, stash, force-push or shared-history rewrite. No commits,
  push or deployment were performed for the preceding experience refresh.
- Keep private Papers material out of the public Site. Preserve immutable
  signed/versioned release assets and use release-index.json for release truth.
- Use headless browser/isolated desktop only. Do not operate the owner's live
  desktop. File-based narration is distinct from enabling spoken agent replies.
- Do not publish the rejected video as a completed product guide.

## Template integration: inspect the actual latest source

Local source: `/home/ff/Projects/ProjectState_Template`.
At handoff, its HEAD is `7e4cb7c` (“fix(core): make outcome validation truthful
and exercise packaged delivery”). Recheck its working tree and any newer local
handoff; a commit ID alone does not establish the newest template contents.
The working tree contains staged updates to AGENTS.md, README.md, STATE.yaml,
upgrade guidance, startup/model-routing prompts, persistent-thread rules,
initialization code and rollout evidence. Preserve these and inspect them as
part of the latest local source. The queued persistent-thread reference is:
`/home/ff/Projects/.projectstate-handoffs/persistent-threads-2026-09-05`.

The prior session adopted that handoff's coordination core into Papers and
appended optional thread rules in Site. This **does not establish that the
papers explain the latest template**. Compare the current template's actual
concepts, workflow, terminology and examples against all affected papers and
site documentation. Update substantive descriptions and diagrams where needed,
preserving historical facts, confidentiality and human-owned acceptance criteria.
Do not activate persistent threads or change models as a migration side effect.

## Existing work to retain and revise

Site has an uncommitted reading-room page (`papers/index.html`), task-oriented
documentation navigation, static table-of-contents links, responsive fixes,
updated copy and a Mermaid change-path diagram. The original mascot artwork
and size were preserved; the new request now authorizes a size change. Inspect
`assets/site.css`, HTML dimensions and the mascot size assertions in validation
scripts together. Apply a 0.75 scale to the relevant rendered mascot dimensions,
check desktop/mobile spacing, and preserve the underlying artwork.

Papers has nine revised Markdown/PDF pairs, a reading guide and improved PDF
build tooling. Sources are `src/*.md`, outputs `out/*.pdf`; rendering is through
`build/check-papers.sh`, `build/make-pdf.sh`, `build/template.html` and
`build/print-pdf.cjs`. Review mascot sizing in paper mastheads and new media
where relevant; do not shrink body text or unrelated controls.

## Video correction — highest product-experience priority

Current files:

- `tutorials/site-orientation.html`
- `assets/media/stateport-field-guide.mp4`
- `assets/media/stateport-field-guide.vtt`
- `assets/media/stateport-field-guide-poster.jpg`

The homepage's “Watch the field guide” CTA and documentation/tutorial links
currently lead to this video. Its 71 seconds show the homepage, StudyState
documentation, documentation index, privacy documentation, Papers and download
page. Technical playback checks passed, but **the subject is wrong for the
owner's intended product demonstration**. Rework the footage, narration,
poster, transcript, captions, chapter labels and referring page copy together.

Preserved production source:
`/home/ff/Projects/.local/stateport-site-media-sep05/`.
Read its README.md, scenes.json, capture.cjs and build-composition.py. It contains
HyperFrames/GSAP composition, screenshots, Edge narration stems, original ambient
music and render logs. Reuse useful production tooling; replace the documentation
footage. HyperFrames animations and a visible cursor were explicitly requested.
Narration, subtle music and motion should help users follow the actual product.

First establish an honest, available product workflow and capture source without
writing to the StatePort checkout. Inspect existing product images in Site
`assets/media/` and Papers `src/assets/`, checking their provenance and age.
Prefer an available isolated product instance if it can be used within the
read-only boundary. Do not fabricate current runtime evidence or present a
mockup/historical capture as the current functioning product. If authentic
capture is unavailable, record the exact dependency instead of substituting
documentation screenshots again.

Suggested storyboard, subject to actual implemented behavior: product home →
open a useful application such as StudyState → set a task → follow the
conversation → review the proposed change → inspect the resulting receipt.
Make the product's purpose understandable before introducing terminology.
Align the cursor and click cues with the actual controls. Inspect rendered
frames at cuts and during cursor motion; check crop, legibility, captions,
audio balance, timing, phone playback and reduced-motion behavior on the site.

The separate historical `stateport-overview.mp4` is the existing 33-second
overview with historical release context and asset checks. Distinguish it from
the new field guide; do not silently rewrite protected historical artifacts.

## Evidence, checks and unresolved delivery

Previous local results, **not acceptance of the requested revisions**:

- Site: validate_repo.py and check_site_quality.py passed; 30 unit tests passed.
  Browser review covered 48 focused views and all 29 sitemap routes in two
  configurations (58 views), including phone and JavaScript-disabled reading.
- Papers: all nine PDFs rebuilt, 118 pages in total, tagged with outlines;
  text-bound checks and visual inspection completed. Papers gate passed.
- Current video: technically playable/captioned and render-checked; owner has
  rejected its content direction despite those results.
- Site's real Windows 11 WSL2 Ubuntu 24.04 complete-product journey remains
  blocked. Signature/bundle, private registry and native-install evidence issues
  remain distinct from local website quality. Do not claim production readiness.

Evidence: Site `evidence/alpha16-public-install-001/summary.md` plus
`experience-browser.json`, `experience-all-pages.json`, `experience-media.json`;
Papers `evidence/papers-experience-001/summary.md` and PDF reports. Browser scripts
and screenshots are under Site `output/experience-review/` (ignored). A local
preview was served at http://127.0.0.1:4173/; verify whether it is still running.

After implementing in the new session, run the smallest representative journey
first, then applicable site checks and the complete Papers build/visual review.
Run each repository's `python3 scripts/projectstate_gate.py` and record honestly
which outcomes pass or remain blocked. Update media provenance and evidence
after regenerating assets. Human acceptance remains separate from passing checks.

## Handoff completion

This session only records the owner's steering and routes the next action here.
Latest-template paper integration, mascot resizing and replacement product
footage are **pending new-session implementation**.


## Resumed-session implementation, 5 September 2026

The deferred work above has now been implemented and locally checked: Papers
explains the current v6 template; rendered mascots are 25% smaller; the new
86-second guide and homepage images show the independent local StatePort
installation. The sample review/apply/receipt/restart journey passed.

The user explicitly authorized installation from local files when the public
installer refused native Linux. The uv-managed installation is at
`/home/ff/.local/share/stateport-local`, open at `http://127.0.0.1:18780`, with
its own services, data and independent source snapshot. Real ProjectState and
StudyState snapshots were imported too; unavailable template Runs/metadata and
external runtime/provider setup remain separate limits.

Current evidence and next actions are in the two repositories' canonical state
and summaries. This original handoff is historical, not a second active queue.
