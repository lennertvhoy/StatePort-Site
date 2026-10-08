# LinkedIn post, English (final)

> Attach `launch/demo/stateport-demo-19s.mp4` (19 s, real product UI, no install shown). Put the install link in the first comment too (see first-comment.md). Best time: Tue-Thu 08:00-10:00 Brussels.

---

I kept losing work when an AI chat ended: the plan, the decisions, the reasons behind them. It all lives in a chat window, and then it's gone.

So I'm building StatePort. The idea is that your project or study plan lives on your own computer, with a receipt for every change you approve, so a new session starts from what's actually there. Today that only works in the built-in study sample: review an activity, approve a change, save a reflection.

It's an early alpha, so here's exactly where it stands. Alpha.24 installs and passes in a clean Windows 11 + WSL2 (Ubuntu 24.04) test VM; real-Windows and reboot results are pending. On Alpha.24 so far I have measured one install from a local copy of the signed files (healthy, a repeat run changed nothing); I have not yet measured the public one-line command, the study sample, restarts or the GitHub template import on it. On the previous release, Alpha.23, the public command installed on a pristine test VM and exited 0 in about 9 minutes (3 of 4 attempts), the study sample ran end to end and survived a service restart and a full WSL restart, the install plan named one API port while the running API answered on another, and importing the StudyState template from GitHub failed because the containers couldn't resolve host names. Alpha.24 carries changes for those, still being verified. A Windows reboot is untested and uninstall hasn't been run on Windows. Please don't put anything important in it.

If you're on Windows 11 with WSL2 and want to try it, I'd like to hear where the install breaks:
https://lennertvhoy.github.io/StatePort-Site/

What would you want an AI to remember for you between sessions?
