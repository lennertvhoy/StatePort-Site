# StatePort launch — what the owner does (one page)

Everything is prepared so clicking "post" is the only step left.

## What was published (2026-09-30)

- Branch `launch/linkedin-20260930`, pushed to `origin`, then fast-forwarded into `main`; GitHub Pages serves `main` directly.
- Live pages tell one honest Alpha.20 story (what works, the exact one-line command, target, known limits, how to report problems):
  - https://lennertvhoy.github.io/StatePort-Site/ (home)
  - https://lennertvhoy.github.io/StatePort-Site/download/ (install command + installer SHA-256 displayed)
  - https://lennertvhoy.github.io/StatePort-Site/releases/ (release status, known limits)
- Measured claims on the pages: Alpha.20 installed from the anonymous one-line route on a genuine Windows 11 25H2 + WSL2 + stock Ubuntu 24.04 VM, twice (exit 0, healthy receipt), and stayed reachable after the last WSL session closed (keep-alive task activated by an interactive logon). Known limits stated plainly: Windows reboot survival not yet measured (qualification run was still in flight at publication), templates/uninstall/reinstall, full UI inventory, and efficiency not yet run; early alpha — do not use for important data.
- Validators before push: `scripts/validate_repo.py` OK, `scripts/check_site_quality.py` OK (34 pages), 63 unit tests OK (run in a clean clone of the branch; the recorded immutable-manifest file modes were applied mode-only, as the qualification run also recorded). `scripts/projectstate_gate.py` honestly exits 1: the full journey (reboot, uninstall/reinstall, human acceptance) is not closed — by design, nothing on the site overclaims it.

## Verification commands (anonymous)

```sh
curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sha256sum
# must print: b83e8376776cd663b6a0aa8098ddde489f0125e033d70e8b1421fb04d1cb8916  -
# (the same digest is displayed on the download page)
curl -fsSI https://lennertvhoy.github.io/StatePort-Site/ | head -1      # 200
curl -fsSI https://lennertvhoy.github.io/StatePort-Site/releases/ | head -1  # 200
```

## Step 0 — test on your own laptop first (5 minutes, changes nothing)

In Ubuntu 24.04 under WSL2, as your normal user:

```sh
bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh) --transport-probe
```

It checks WSL2, Ubuntu 24.04, systemd, the Windows build and your network, verifies the signed manifests, and installs nothing. Expected last line: `StatePort Alpha.20 transport probe passed ... installer was not executed.` If it stops, the message names the missing prerequisite (most often: systemd not enabled in WSL; run `wsl --shutdown` in PowerShell after enabling it). Then run the real install (without `--transport-probe`), answer the two confirmations, and open the printed local URL. Only post once that works on your machine. Known: after a Windows reboot you may need to log in and open WSL again (reboot survival not yet measured).

## What the owner does to post (10 minutes)

1. Open LinkedIn → Start a post. Copy the body text from `launch/post-en.md` (between the `---` rule and the end; skip the italic note above it).
2. Attach the demo video `launch/demo/stateport-demo-24s.mp4` (24 s, 5.3 MB; real product UI, trimmed from the published 33 s overview — the outdated closing status card is cut). Alternative: attach images instead — `launch/screenshots/frame-conversation.png`, `frame-result.png`, `stateport-hero-preview.png` (LinkedIn takes video OR images in one post; the video carries the story better).
3. Post it. Dutch version ready in `launch/post-nl.md` for a follow-up post if you want one.
4. Immediately add the first comment from `launch/first-comment.md` (EN top, NL below) and pin it.
5. Optional 10-second check: LinkedIn's link preview uses `assets/media/stateport-social-card.png`; this session could not visually inspect that image (no image input) — glance at the preview and confirm it says nothing stale.

## Known limits of this kit

- The demo video was recorded in August 2026 (pre-Alpha.20 build); the product UI journey it shows is the same one the site presents today. A fresh Alpha.20 guest capture was not needed (site assets sufficed); no CAPTURE-REQUEST.md was written.
- Windows reboot qualification (`~/.local/state/stateport/alpha20-publish/gov-reboot-1259/`) had not produced a result at publication time; if it lands green, update the releases page wording in a small follow-up commit.
