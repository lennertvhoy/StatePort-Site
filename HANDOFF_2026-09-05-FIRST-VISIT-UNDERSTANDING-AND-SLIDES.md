# Next-session handoff — first-visit understanding and programmable slides

## Owner direction and scope of this handoff

The owner requested this handoff on 5 September 2026, with no loss of prior
information. Implementation belongs to the next slice/session. The message was
dictated; preserve its intent rather than treating loose phrasing as a technical
specification.

The public experience must help people open the site and understand StatePort.
StatePort is complex and capable of many things; that breadth must not prevent
visitors from understanding its value. The owner is concerned that confusion
will hurt retention. This is an owner concern, not an observed retention metric.

The owner also wants slides that a coding agent can create, update, maintain,
use and show programmatically, through an API or a suitable slide framework,
with interoperability with existing PowerPoint presentations. No framework,
provider, subscription, hosting service or API design has been selected.
This is a related deliverable, not permission to make a slide deck the required
way to understand the homepage.

## Read order and preserved authority

Read AGENTS.md, PROJECT.md, STATE.yaml and the current slice evidence in each
repository before work. This handoff directs the next action; it does not replace
canonical state, weaken existing acceptance, or mark the current release done.
The original HANDOFF_2026-09-05-PRODUCT-VIDEO-AND-PAPERS.md is retained in full as
historical context, including its appended implementation result.

- Site: /home/ff/Projects/StatePort-Site.
- Papers: /home/ff/Projects/StatePort-Papers (private).
- Product: /home/ff/Projects/StatePort remains read-only while another agent
  works there. Do not change its checkout or disturb its runtime.
- Preserve staged/unstaged changes, untracked evidence, original slide files,
  historical media and immutable signed/versioned release bytes.
- Keep private Papers and private presentation content out of the public Site.
- Use isolated/headless GUI automation; never the owner's live desktop.
- No analytics, tracking or third-party runtime scripts on the public site.
- Keep the queued Site ProjectState refresh notices while the native outcome
  remains blocked. Optional persistent threads stay inactive unless selected.

## First priority: make the product understandable

Start with the current public homepage and its real installed-product example.
Identify what a newcomer must understand before they encounter internal terms,
multiple product concepts, template families, architecture or release history.
Do not start by adding more sections, animations, diagrams or documentation.

Proposed work sequence (agent proposal, not invented human acceptance):

1. Record the current first-visit path and where it assumes prior knowledge.
   Draft a plain-language answer to: who is this for, what can I accomplish,
   what happens when I use it, and why would I come back?
2. Choose one honest, concrete before/action/after example grounded in verified
   behavior. The installed StudyState Sample currently supplies real review,
   approval, saved reflection and receipt evidence. Label sample behavior;
   do not imply general AI execution or unavailable template Runs work.
3. Arrange the first screen and next few steps around that example and one
   clear next action. Explain specialized terms when needed. Reveal breadth
   progressively, keeping deeper technical material accessible.
4. Keep homepage, screenshots, guide narration/transcript, getting-started and
   public reading guide consistent. Reuse the authentic footage where useful;
   technical video quality alone does not establish comprehension.
5. Review the experience on phone, desktop and without JavaScript. Then use a
   short comprehension check with a first-time reader when one is available.
   Do not contact people without authorization; agent review is a preliminary
   check, not evidence of a novice reader's understanding.

Proposed comprehension prompts after a brief first visit: “What is StatePort
for?”, “What would you use it to do?”, “What does this example save or change?”,
and “What would you do next?” Record actual answers and confusion without
coaching. A 30–60 second first-impression check can be a practical starting
point, not a fixed owner-approved threshold. If no reader is available, mark
human comprehension not_run and leave a concrete reviewable experience.

Do not claim retention improved from a redesign, automated tests, or these
answers. Comprehension is a useful leading signal; retention needs separate
longitudinal evidence and any measurement must respect the site's privacy rules.

## Related requirement: slides maintained and presented through code

First inventory existing local PowerPoint files and any existing slide tools,
APIs or build conventions. Locate representative decks, inspect confidentiality,
and work on copies. If the intended decks cannot be identified locally, record
the exact missing input rather than asserting compatibility with generic files.

Before choosing a framework, test a small end-to-end example:

- A documented local command or callable API creates a short StatePort deck
  from editable source and assets, updates an existing slide, and rebuilds it.
- The coding agent can open/show it in an isolated presentation viewer and
  navigate it. Record whether “API” means a local library, CLI wrapper, HTTP
  endpoint or a hosted service; prefer the smallest mechanism meeting the need.
- Export a real .pptx that opens correctly in a PowerPoint-compatible viewer.
  Test actual PowerPoint if available; do not label another viewer equivalent.
- Import or adapt a copy of an existing PowerPoint deck, change content through
  code, export it, and inspect the result. Test editability and preservation of
  text, images, layouts, themes, notes, links, fonts and important media/motion.
  Explicitly record unsupported features and whether round-trip editing works.
  PDF export or slides flattened into images do not establish editable PPTX
  interoperability. Export-only and round-trip support are distinct claims.
- Keep editable source, assets, build instructions and dependencies together;
  show that another agent/session can make a change and reproduce the deck.
  Provide a shareable presentation artifact without requiring private tooling
  or credentials merely to view its content.

Use the applicable presentation skill when implementing. Verify current
framework capabilities against primary documentation then; no framework
recommendation or compatibility claim has been researched in this handoff.
A short deck may reuse the same concrete product narrative as the site.
Keep framework exploration bounded to that proof, rather than building a new
presentation platform. Do not add hosted services, costs, credentials or public
publication of existing decks merely to satisfy a loosely interpreted API wish.

## Completed baseline — preserve rather than redo

The preceding implementation is published: Site b431e63, Papers 85c6c39.
GitHub Pages built the Site commit; all 43 changed public files anonymously
matched local bytes. Exact receipt:
/home/ff/Projects/.local/stateport-product-guide-sep05/publication-verification.json.
Recheck actual repository and remote state on resume; these are historical
provenance, not mutable-state commit binding.

- Public site: https://lennertvhoy.github.io/StatePort-Site/.
- Four fresh homepage screenshots show the independent installed product.
  Gallery aspect ratio/phone fit are fixed; all 12 gallery views passed.
- New guide: 86 seconds, real StatePort sample workflow, visible animated cursor,
  narration, quiet music, captions, poster and matching transcript/chapters.
  The historical 33-second overview is unchanged; the rejected documentation
  tour and earlier captures remain preserved outside the public assets.
- Header/footer and paper masthead mascot rendering is 25% smaller; artwork
  is preserved. Latest ProjectState v6 concepts are explained in template docs
  and affected Papers content.
- Nine private Papers PDFs rebuilt from Markdown: 120 pages, reviewed renders,
  outlines and no out-of-page text. Papers remains private; those private PDFs
  were not copied into the public reading hub.
- Site checks: validators and 30 unit tests passed, 58 sitemap browser views
  passed. Papers build and outcome gate passed. Human acceptance is pending.

Media source, narration, captured scenes, render scripts and logs:
/home/ff/Projects/.local/stateport-product-guide-sep05/.
Earlier source: /home/ff/Projects/.local/stateport-site-media-sep05/.
Site visual evidence: output/product-refresh/ and the current slice JSON files.
Papers sources/outputs: src/*.md, out/*.pdf; build/check-papers.sh;
visual evidence: build/.work/product-refresh-review/ and current slice summary.

## Independent local installation and exact limits

The public installer refuses native Linux. The owner explicitly authorized the
local-file fallback; this is a separate local installation, not a repaired or
qualified public Windows release.

- Open http://127.0.0.1:18780 or application menu “StatePort (Local)”.
- Root: /home/ff/.local/share/stateport-local; control: stateport-local
  start|stop|restart|status|logs. Separate enabled systemd user services and XDG
  data use loopback ports 18780, 18790 and 18791.
- Independent source snapshot: 28f72db7ef8f30e6a3a24641c4d61f8b58d5a297;
  no development links/remotes. uv manages Python 3.13.15 and hashed runtime
  dependencies. The frontend was built from locked dependencies in the copy.
  “Rust package management thing” was interpreted as uv; the owner did not
  explicitly confirm the manager name. Do not silently replace it on resume.
- StudyState Sample: Catalog install, review/approve Start, review/apply a
  reflection, inspect receipt, restart service, verify saved reflection and
  50% progress all passed. This was not a machine reboot test.
- Independent real ProjectState and StudyState template snapshots were imported.
  Imported ProjectState reports unavailable metadata and Runs. Successful
  import does not establish successful template execution.
- External execution host/provider configuration is absent; worker execution
  is disabled. Credentials and model settings were not copied or changed.

Evidence: Site evidence/alpha16-public-install-001/{summary.md,
local-installation.json,experience-media.json,experience-all-pages.json,
product-gallery.json}; local installation README.md, installation-verification.json,
installation-source.json and template-sources.json.

## Unfinished work must remain visible

Alpha.16 signature predecessor lookup fails fresh package preflight; its seven
GHCR packages are private and anonymous access fails. Changing package-wide
visibility would expose older versions without reviewed public provenance.
A qualified additive successor and genuine fresh Windows 11 WSL2 Ubuntu 24.04
complete-product lifecycle/three-template proof remain open. Do not rewrite
immutable Alpha.16 or substitute the local sample for native acceptance.

Site primary journey and outcome gate remain blocked; Papers human acceptance
is pending. Preserve the unrelated untracked Site
 evidence/alpha14-public-install-001/summary.md. Continue to keep release
qualification, local runtime setup, public understanding and slide compatibility
as distinct claims, even if worked on in the same future session.

## Exact next action

Resume from both repositories' canonical records and this handoff. Inspect the
current first-visit experience, draft one concrete narrative and record its
comprehension questions before changing the site. Then inventory existing decks
and prove the smallest programmable edit/present/PPTX interoperability workflow.
Do not lose the current release blockers when scheduling this next work. This
handoff adds no implementation or human acceptance claim.
