# StatePort launch — what the owner does (one page)

Everything is prepared so clicking "post" is the only step left.

## What the pages say (updated 2026-10-08 for Alpha.24)

- The site was published on 2026-09-30 with the Alpha.20 story (branch `launch/linkedin-20260930`, fast-forwarded into `main`; GitHub Pages serves `main` directly). On 2026-10-01 the one-line route switched to Alpha.21, on 2026-10-03 to Alpha.22, on 2026-10-07 to Alpha.23, and on 2026-10-08 (branch `copy/alpha24`) it switches to Alpha.24; each flip rewrote the status claims from that release's measured results. The Alpha.20 to Alpha.23 history stays on the release status page.
- Live pages tell one honest Alpha.24 story (what is measured, the exact one-line command, target, known limits, how to report problems):
  - https://lennertvhoy.github.io/StatePort-Site/ (home)
  - https://lennertvhoy.github.io/StatePort-Site/download/ (install command + installer SHA-256 displayed)
  - https://lennertvhoy.github.io/StatePort-Site/releases/ (release status, known limits)
- Install facts: the installer SHA-256 is `4c7499e60b82fded33672dfd472fea87bca8ea96b74a579affc1681af10181fd`. Wording to use for Alpha.24: it installs and passes in a clean test VM; real-Windows and reboot results pending (reboot: not measured). Measured on Alpha.24 on a Windows 11 + WSL2 + stock Ubuntu 24.04 virtual machine (a KVM guest, not bare metal) reset to a clean snapshot: the public one-line command exited 0 in 474 seconds (one attempt); all services healthy; a qualification install from a local copy of the signed files also exited 0 and a second installer run changed nothing; the bundled study sample ran end to end and its data survived a StatePort service restart and a WSL distribution restart (7 of 7 checks both times); importing the StudyState template from GitHub worked; `systemctl --user restart stateport-accepted.target` restarted all three containers; the manifest ports of API (18097), web (18974) and worker (18441) equal the published ports; the web service has its own outbound network (it resolved github.com) while the API and worker are internal-only (could not resolve external names, by design). State plainly that the web service now has outbound internet access (for GitHub import and AI provider connections; the provider connection itself was not tried). Not measured on Alpha.24: the slow keep-alive registration case (did not occur), a Windows reboot, uninstall and reinstall on Windows, ProjectState and a third template, a full UI audit, resource use. Alpha.23 history (public command): exit 0 in about 9 minutes on a pristine machine, 3 of 4 attempts (the 4th crashed in the keep-alive registration on a 120 s PowerShell timeout); study sample end to end and data kept after a service restart and a WSL restart; plan port 18464 vs API answering on 18447; GitHub template import failed because the containers could not resolve external host names. These three are what Alpha.24 changed. Never write "verified" until the owner has run it on real Windows. Alpha.22 history: three runs on a reset machine, the second and third healthy after a test-setup fix (plan port 18578, API answered 18561). Alpha.21 history: healthy on 2 of 3 fresh test installs, one stopped by `package_installation_invalid` (wait a minute and run the same command again; it is on the troubleshooting page).
- Measured on Alpha.21 and NOT repeated on Alpha.22, Alpha.23 or Alpha.24, as the pages say it: the study sample in the browser, templates import from a local Git folder; undo, export and import, backup and restore work through the API. Not working on Alpha.21 and not re-measured on an installed Alpha.24: coding-agent runs, chat replies, restore from the interface, provider actions in the interface, the workbench terminal and files tools, per-application workspaces, the standing-authority and updater pages, and the background worker. The Linux checks of the Alpha.22 code (50 end-to-end scenarios: 40 worked, 0 broken, 1 could not be tested, 9 not run; installer lifecycle lab 10 of 10) stay attributed to Alpha.22 on the pages. Not measured: a Windows reboot, uninstall on Windows, undo in the browser, restarting the web service.
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

It checks WSL2, Ubuntu 24.04, systemd, the Windows build and your network, verifies the signed manifests, and installs nothing. Expected last line: `StatePort Alpha.24 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.` If it stops, the message names the missing prerequisite (most often: systemd not enabled in WSL; run `wsl --shutdown` in PowerShell after enabling it). Then run the real install (without `--transport-probe`), answer the two confirmations, and open the printed local URL. Only post once that works on your machine. Known: a package check stopped one of three Alpha.21 installs with `package_installation_invalid`; wait a minute and run the same command again. After a Windows restart you may need to sign in and open Ubuntu again (a planned restart was not measured).

## What the owner does to post (10 minutes)

1. Open LinkedIn → Start a post. Copy the body text from `launch/post-en.md` (between the `---` rule and the end; skip the italic note above it).
2. Attach the demo video `launch/demo/stateport-demo-19s.mp4` (19 s, 2.9 MB; real product UI, trimmed from the published 33 s overview — the outdated closing status card is cut). Alternative: attach images instead — `launch/screenshots/frame-conversation.png`, `frame-result.png`, `stateport-hero-preview.png` (LinkedIn takes video OR images in one post; the video carries the story better).
3. Post it. Dutch version ready in `launch/post-nl.md` for a follow-up post if you want one.
4. Immediately add the first comment from `launch/first-comment.md` (EN top, NL below) and pin it.
5. Optional 10-second check: LinkedIn's link preview uses `assets/media/stateport-social-card.png`; this session could not visually inspect that image (no image input) — glance at the preview and confirm it says nothing stale.

## Known limits of this kit

- The demo video is the site overview cut to 19 s (the "undoable" segment removed because only one undo exists, the last evidence update in the study sample). It was recorded in August 2026 on an earlier build and shows the study sample and a receipt; it does not show installing.
- The link-preview card (`assets/media/stateport-social-card.png`) was regenerated after publication: its subtitle now reads "AI-assisted work, saved in files on your own computer." (it said "A durable home ..."). LinkedIn caches previews, so refresh it in the Post Inspector before you post.
- A planned Windows reboot was not measured on Alpha.21, Alpha.22, Alpha.23 or Alpha.24 (the test machine cannot reboot its nested WSL), and uninstall has not been run on Windows. If either is measured later, update the releases page wording in a small follow-up commit.
