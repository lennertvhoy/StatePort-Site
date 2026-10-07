# LinkedIn post, English (final)

> Attach `launch/demo/stateport-demo-19s.mp4` (19 s, real product UI, no install shown). Put the install link in the first comment too (see first-comment.md). Best time: Tue-Thu 08:00-10:00 Brussels.

---

I kept losing work when an AI chat ended: the plan, the decisions, the reasons behind them. It all lives in a chat window, and then it's gone.

So I'm building StatePort. The idea is that your project or study plan lives on your own computer, with a receipt for every change you approve, so a new session starts from what's actually there. Today that only works in the built-in study sample: review an activity, approve a change, save a reflection.

It's an early alpha, so here's exactly where it stands. The Alpha.23 installer for Windows 11 + WSL2 (Ubuntu 24.04) installs and passes in a clean test VM; real-Windows and reboot results are pending. That test ran from a local copy of the signed files, not the public one-liner, and I haven't repeated the browser walk-through on Alpha.23 yet. One measured issue stays open: the install plan named one API port while the running API answered on another; the address the installer prints is the right one. On Alpha.21 the study sample worked in the browser: one click opens it, you approve the exact change, save a reflection, get a receipt, and it's still there after a reload. Chat replies, coding-agent runs and container workspaces didn't work on Alpha.21, and I haven't re-measured them. A Windows reboot is untested and uninstall hasn't been run on Windows. Please don't put anything important in it.

If you're on Windows 11 with WSL2 and want to try it, I'd like to hear where the install breaks:
https://lennertvhoy.github.io/StatePort-Site/

What would you want an AI to remember for you between sessions?
