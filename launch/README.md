# StatePort launch — what the owner does (one page)

Everything is prepared so clicking "post" is the only step left.

## What the pages say (updated 2026-10-01 for Alpha.21)

- The site was published on 2026-09-30 with the Alpha.20 story (branch `launch/linkedin-20260930`, fast-forwarded into `main`; GitHub Pages serves `main` directly). On 2026-10-01 the one-line route switched to Alpha.21 and the pages were rewritten to the Alpha.21 measurements. On 2026-10-03 (branch `copy/alpha22`, not yet published when this was written) the route switches to Alpha.22 and every status claim is rewritten from the measured Alpha.22 results. The Alpha.20 and Alpha.21 history stays on the release status page.
- Live pages tell one honest Alpha.22 story (what is measured, the exact one-line command, target, known limits, how to report problems):
  - https://lennertvhoy.github.io/StatePort-Site/ (home)
  - https://lennertvhoy.github.io/StatePort-Site/download/ (install command + installer SHA-256 displayed)
  - https://lennertvhoy.github.io/StatePort-Site/releases/ (release status, known limits)
- Install facts: the installer SHA-256 is `60db0ca4dc590eeadd328c34bd20e1cfe202ac00f066289272fa12229d03db43`. Wording to use for Alpha.22: it installs and passes in a clean test VM; real-Windows and reboot results pending. Measured on a fresh Windows 11 + WSL2 + stock Ubuntu 24.04 virtual machine (reset to a clean snapshot each run): three runs, the first stopped at the image download because the images had not been uploaded yet (a test-setup mistake), the second and third finished healthy; the third passed every check (all services healthy, web page and API answered, a second run of the installer reported it was already installed and changed nothing, the keep-alive task registered with start-up, sign-in and 10-minute triggers). Those installs used a local copy of the signed files, not the public one-liner, and the install time was not recorded. The reboot result is "not measured". Never write "verified" until the owner has run it on real Windows. Alpha.21 history: healthy on 2 of 3 fresh test installs, one stopped by `package_installation_invalid` (wait a minute and run the same command again; it is on the troubleshooting page).
- Measured on Alpha.21 and NOT repeated on Alpha.22, as the pages say it: the study sample opens with one click and runs in the browser from start to receipt with the saved state kept after a reload; templates import from a local Git folder; undo, export and import, backup and restore work through the API. Not working on Alpha.21 and not re-measured on an installed Alpha.22: coding-agent runs, chat replies, restore from the interface, provider actions in the interface, the workbench terminal and files tools, per-application workspaces, the standing-authority and updater pages, and the background worker. On Alpha.22 the pages also state the Linux checks of the Alpha.22 code (50 end-to-end scenarios: 40 worked, 0 broken, 1 could not be tested, 9 not run; installer lifecycle lab 10 of 10) as exactly that, not as an installed-Windows measurement. Not measured: a Windows reboot, uninstall on Windows, undo in the browser on Alpha.22, restarting the web service.
- Validators: `scripts/validate_repo.py`, `scripts/check_site_quality.py` and the unit tests are run in a clean clone of the branch before anything is pushed. `scripts/projectstate_gate.py` honestly exits 1: the full journey (reboot, uninstall/reinstall, human acceptance) is not closed, by design, and nothing on the site overclaims it.

## Verification commands (anonymous)

```sh
curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sha256sum
# must print: 5fc574f25072f1c801cd40a098126eb230934e8af4f18f8e5c1518955d0cc9e0  -
# (the same digest is displayed on the download page)
curl -fsSI https://lennertvhoy.github.io/StatePort-Site/ | head -1      # 200
curl -fsSI https://lennertvhoy.github.io/StatePort-Site/releases/ | head -1  # 200
```

## Step 0 — test on your own laptop first (5 minutes, changes nothing)

In Ubuntu 24.04 under WSL2, as your normal user:

```sh
bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh) --transport-probe
```

It checks WSL2, Ubuntu 24.04, systemd, the Windows build and your network, verifies the signed manifests, and installs nothing. Expected last line: `StatePort Alpha.22 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.` If it stops, the message names the missing prerequisite (most often: systemd not enabled in WSL; run `wsl --shutdown` in PowerShell after enabling it). Then run the real install (without `--transport-probe`), answer the two confirmations, and open the printed local URL. Only post once that works on your machine. Known: a package check stopped one of three Alpha.21 installs with `package_installation_invalid`; wait a minute and run the same command again. After a Windows restart you may need to sign in and open Ubuntu again (a planned restart was not measured).

## What the owner does to post (10 minutes)

1. Open LinkedIn → Start a post. Copy the body text from `launch/post-en.md` (between the `---` rule and the end; skip the italic note above it).
2. Attach the demo video `launch/demo/stateport-demo-19s.mp4` (19 s, 2.9 MB; real product UI, trimmed from the published 33 s overview — the outdated closing status card is cut). Alternative: attach images instead — `launch/screenshots/frame-conversation.png`, `frame-result.png`, `stateport-hero-preview.png` (LinkedIn takes video OR images in one post; the video carries the story better).
3. Post it. Dutch version ready in `launch/post-nl.md` for a follow-up post if you want one.
4. Immediately add the first comment from `launch/first-comment.md` (EN top, NL below) and pin it.
5. Optional 10-second check: LinkedIn's link preview uses `assets/media/stateport-social-card.png`; this session could not visually inspect that image (no image input) — glance at the preview and confirm it says nothing stale.

## Known limits of this kit

- The demo video is the site overview cut to 19 s (the "undoable" segment removed because only one undo exists, the last evidence update in the study sample). It was recorded in August 2026 on an earlier build and shows the study sample and a receipt; it does not show installing.
- The link-preview card (`assets/media/stateport-social-card.png`) was regenerated after publication: its subtitle now reads "AI-assisted work, saved in files on your own computer." (it said "A durable home ..."). LinkedIn caches previews, so refresh it in the Post Inspector before you post.
- A planned Windows reboot was not measured on Alpha.21 or Alpha.22 (the test machine cannot reboot its nested WSL), and uninstall has not been run on Windows. If either is measured later, update the releases page wording in a small follow-up commit.
