# First-visit understanding review — 5 September 2026

Baseline: public homepage fetched anonymously before editing; preserved locally
at `/home/ff/Projects/.local/stateport-first-visit-sep05/public-before.html`.
It opened with “Applications that keep their state”, two video routes, three
reader paths and a historical video before the concrete sample. “Ask. Remember.
Change. Undo.” implied a broader journey than the current sample evidence.
These are agent observations, not novice feedback or a measured retention issue.

Chosen narrative: a student returns to a study session. The sample keeps the
goal and activities; the student reviews Start, approves the change to in
progress, reviews and saves a reflection, and can return to that saved progress
after a local service restart. A receipt records the applied operation. It does
not verify learning, establish general AI execution, or prove reversibility.

Implementation: one hero action, “Follow the study example”, jumps directly to
the existing screenshots. The example now precedes reader routes and historical
video. Getting-started, field-guide introduction and public reading guide use
the same example. Authentic narration/transcript and screenshot bytes are
unchanged; the introduction now defines receipt and explicitly says service
restart. Breadth and release details remain accessible.

Agent preliminary check: the page identifies students/project owners, describes
saved progress and reflection, explains review before change, and names a useful
next action. This establishes the presence of answers, not human comprehension.

## Human comprehension check: not_run

No first-time reader has been recruited or contacted. When one is available,
let them visit the homepage briefly without coaching, then record verbatim:

1. What is StatePort for?
2. What would you use it to do?
3. What does this example save or change?
4. What would you do next?

Record device, visit duration, route, actual answers and confusion. A 30–60
second initial visit is a proposed practical starting point, not an acceptance
threshold. Do not supply expected answers before the reader responds. Visual
polish, these prompts and automated checks do not prove improved retention.
Retention measurement needs separate longitudinal evidence and privacy review.

## Checks

Headless Chromium 390×1000 and 1440×1000, JavaScript enabled and disabled, on
homepage, guide, getting-started and public papers hub: all 16 views passed
without overflow or page errors; primary action landed at #journey. Phone and
desktop no-JS hero screenshots inspected. Existing quality contract and 30 tests
passed. The contract now checks example-before-video order and the new primary
action instead of requiring the old historical-video CTA.

Browser script, results, screenshots, slide render experiments and build receipts:
`/home/ff/Projects/.local/stateport-first-visit-sep05/build/`.
