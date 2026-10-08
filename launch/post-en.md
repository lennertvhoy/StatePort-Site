# LinkedIn post, English (final)

> Attach `launch/demo/stateport-demo-19s.mp4` (19 s, real product UI, no install shown). Put the install link in the first comment too (see first-comment.md). Best time: Tue-Thu 08:00-10:00 Brussels.

---

I kept losing work when an AI chat ended: the plan, the decisions, the reasons behind them. It all lives in a chat window, and then it's gone.

So I'm building StatePort. The idea is that your project or study plan lives on your own computer, with a receipt for every change you approve, so a new session starts from what's actually there. Today that only works in the built-in study sample: review an activity, approve a change, save a reflection.

It's an early alpha, so here's exactly where it stands. The public one-line command installed Alpha.24 on a pristine Windows 11 + WSL2 (Ubuntu 24.04) test machine (a KVM guest, not bare metal) and exited 0 in 474 seconds, on one attempt. The bundled study sample ran end to end: start an activity, review the exact change, approve it, receipt, reflection, with the result read back from disk — and it survived restarting StatePort and a full WSL restart. Importing the StudyState template from GitHub now works inside StatePort (it failed on Alpha.23 because the containers couldn't resolve host names); the web service now has outbound internet access through its own network, while the API and worker stay isolated. The install plan and the running API now agree on the port. Not measured on Alpha.24: a Windows reboot, uninstall on Windows, ProjectState and a third template, a full UI audit, resource use. Please don't put anything important in it.

If you're on Windows 11 with WSL2 and want to try it, I'd like to hear where the install breaks:
https://lennertvhoy.github.io/StatePort-Site/

What would you want an AI to remember for you between sessions?
