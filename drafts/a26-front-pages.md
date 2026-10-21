# Draft: front-page prose for Alpha.26

**This file is a draft. Nothing in it is published.** It holds the wording
proposed for the three front pages whose version statements are flipped by the
release tool at release time: `index.html`, `download/index.html` and
`releases/index.html`. The pages themselves were not changed on this branch.

The docs pages under `docs/` already describe Alpha.26 and are committed.

## How to use this draft

Each block below gives the surface, the text as it reads now, and the text
proposed for Alpha.26. Two rules apply when the release tool flips the
version:

1. **Do not edit the pinned paragraph.** The block labelled *Pinned* is
   checked word for word by `scripts/validate_repo.py` and
   `scripts/check_site_quality.py`. It names the release that was measured.
   It has to be replaced by the tool together with the release index, not by
   hand, or the validators refuse the site.
2. **Do not invent a measurement.** Every sentence about what was measured
   needs a result. Where the result does not exist yet, the sentence stays
   empty of numbers, or it names the placeholder that will carry the number
   once it exists.

---

## `index.html`

### Availability banner (under the hero)

Now:

> **Alpha.24 has a one-line installer for Windows 11 + WSL2: it installs and passes in a clean test VM; real-Windows and reboot results pending. Early alpha, known limits below.** Get the install command →

Proposed:

> **Alpha.26 has a one-line installer for Windows 11 + WSL2. Early alpha, known limits below.** Get the install command →

### Overview caption (under the clip)

Now:

> This clip shows the real interface, recorded in August 2026 on an earlier development build. Screens in Alpha.24 may differ. It shows the study sample and a receipt; it does not show installing or setting anything up.

Proposed:

> This clip shows the real interface, recorded in August 2026 on an earlier development build. Screens in Alpha.26 may differ. It shows the study sample and a record of a change; it does not show installing or setting anything up.

### The line under the hero (second paragraph of the intro)

Now:

> StatePort Alpha.24 is an early alpha. If you have a Windows 11 computer with WSL2 and Ubuntu 24.04, you can install it with one command. Use a test machine and test data only.

Proposed:

> StatePort Alpha.26 is an early alpha. If you have a Windows 11 computer with WSL2 and Ubuntu 24.04, you can install it with one command. Use a test machine and test data only.

### The "state is saved on disk" paragraph

Now:

> State is saved on disk, not held in a chat window. On Alpha.21 the study sample's saved state was still there after a page reload; that was measured again on Alpha.23 and Alpha.24 through the product's own interface, with the saved data still there after a StatePort service restart and a full WSL distribution restart. Whether StatePort keeps running after the last Ubuntu window closes was not measured on Alpha.23 or Alpha.24, and a Windows reboot is not measured (reboot: not measured).

Proposed:

> State is saved on disk, not held in a chat window. On the release before this one, the study sample's saved state was still there after a page reload, and still there after a StatePort service restart and a full WSL distribution restart. Whether StatePort keeps running after the last Ubuntu window closes, and what happens after a Windows restart, are not measured yet.

### Status section

Heading, now:

> Alpha.24 is the current public alpha, and it is an early alpha

Heading, proposed:

> Alpha.26 is the current public alpha, and it is an early alpha

**Release label**, now:

> **Release label.** Alpha.24 is the current public alpha. Its signed release index marks it a qualification candidate; it is not yet qualified. The index also declares rollback unsupported: there is no supported way back to an earlier alpha, and data saved by one alpha may not work in another.

Proposed:

> **Release label.** Alpha.26 is the current public alpha, and it is an early alpha. There is no supported way back to an earlier release: you can move forward to a newer one, and data saved by one release may not be usable in another.

**What works today**, now (one long paragraph about the Alpha.24 and Alpha.23 test virtual machines, the 474 second install, the study sample and the GitHub import).

Proposed:

> **What works today.** Alpha.26 installs from one command on Windows 11 with WSL2 and Ubuntu 24.04. It gives you a web interface, an API, storage and a sandbox on your own machine, and an address on your own computer that nobody else can reach. You open an application, run its check, ask a model to work on a copy, read the diff it proposes, and apply it or reject it. The measurements for this release are not in yet: how long the install takes, what happens after a Windows restart, and how much memory and disk it uses are still open. The install, the study sample and an import from GitHub were measured on the previous release in a Windows 11 test virtual machine, which is a virtual machine and not a physical computer.

**Not working yet**, now (a long paragraph about the Alpha.21 failures).

Proposed:

> **Not working yet.** You cannot go back to an older release. The Decision Log template is not published yet, so it cannot be imported. Chat answers questions about an application and never runs tools or changes anything. One undo exists, for the last evidence update in the study sample. A backup holds the files of one application, not its history. There is no team, no hosted version and no supported way to reach it over a network. The measurements listed above are not in yet. The full list is on current limitations.

### The exact status statement

**Pinned.** The paragraph that begins *StatePort 0.1.0-alpha.24 is the current
public alpha* is checked word for word by the validators. It is replaced by
the release tool together with the release index, and it must not be edited
by hand. The same paragraph appears in `download/index.html` and
`releases/index.html`.

### The "measured" list item

Now:

> On Alpha.24: one-command install (the public command exited 0 in 474 seconds, one attempt, in a local Windows 11 test virtual machine); the bundled study sample end to end, with the saved data kept after a service restart and a full WSL restart; importing the real StudyState template … from its public GitHub address, which offers a read-only inspect action only. On Alpha.21 (not repeated on Alpha.24): …

Proposed:

> On the previous release: one-command install (the public command exited 0 in 474 seconds, one attempt, in a local Windows 11 test virtual machine); the bundled study sample end to end, with the saved data kept after a service restart and a full WSL restart; importing the StudyState template from its public GitHub address. For Alpha.26 the results are not in yet: <!-- facts:install-seconds -->, <!-- facts:journey-result -->, <!-- facts:reboot-result -->, <!-- facts:memory-mb --> and <!-- facts:disk-gb -->.

---

## `download/index.html`

### Metadata

`title`, `og:title`, the JSON-LD `name` and `description`, and the meta
description all carry the release label. The tool flips them together with
the install route.

### Headline and the line under it

Now:

> Install StatePort Alpha.24
>
> **Alpha.24 installs and passes in a clean test VM; real-Windows and reboot results pending. It is an early alpha with known limits, listed below.**

Proposed:

> Install StatePort Alpha.26
>
> **Alpha.26 installs on Windows 11 with WSL2 and Ubuntu 24.04. It is an early alpha with known limits, listed below.**

### The early-alpha notice

Now:

> **StatePort is in early alpha. Do not use it for important data.** Use test data and keep your own backups. Alpha.24 is meant for one person on one Windows 11 computer; it is not production software. Its signed release index marks it a qualification candidate; it is not yet qualified. The index also declares rollback unsupported, so there is no supported way back to an earlier alpha.

Proposed:

> **StatePort is in early alpha. Do not use it for important data.** Use test data and keep your own backups. Alpha.26 is meant for one person on one Windows 11 computer; it is not production software. There is no supported way back to an earlier release.

### The "tested on" list

Now: three items, *Tested on Alpha.24*, *Tested on Alpha.23*, *Tested on Alpha.21, not repeated on Alpha.24*, and *Not working yet*.

Proposed:

> - **What this release does.** One command installs it. It asks for your password and for two typed confirmations, then prints the address to open and the commands that manage it. You open an application, run its check, ask a model to work on a copy, and apply or reject what it proposes.
> - **Measured on the previous release.** The install, the study sample, a service restart, a full WSL restart and an import from GitHub, in a Windows 11 test virtual machine. The public command took 474 seconds there, once.
> - **Not measured yet for this release.** How long the install takes: <!-- facts:install-seconds -->. The whole journey on a clean machine: <!-- facts:journey-result -->. What happens after a Windows restart: <!-- facts:reboot-result -->. Memory and disk at idle: <!-- facts:memory-mb --> and <!-- facts:disk-gb -->. Upgrading in place: <!-- facts:upgrade-result -->. Removing StatePort on Windows: <!-- facts:removal-result -->. Importing the three templates: <!-- facts:import-result -->.
> - **Not working yet.** You cannot go back to an older release. The Decision Log template is not published yet. Chat answers questions and never changes anything. One undo exists. A backup holds the files of one application.

### The dry-run line

Now:

> A passing dry run ends with a line that starts `StatePort Alpha.24 transport probe passed`.

Proposed:

> A passing dry run ends with a line that says the transport probe passed and that the installer was not executed.

### The known issue under the install command

Now:

> Open Ubuntu 24.04 in WSL2 and run this as your normal Ubuntu user. **Known issue in Alpha.24:** run `cd /tmp` first; started from your home folder the installer stops at step 5 of 7 with `volume_create_failed` (details).

Proposed:

> Open Ubuntu 24.04 in WSL2 and run this as your normal Ubuntu user, in any folder including your home folder. The `cd /tmp` workaround that Alpha.24 needed is no longer needed.

### How long the install takes

Now:

> Expect it to take several minutes: the Alpha.24 public command took 474 seconds (about 8 minutes) once on a test virtual machine (a local KVM guest, not bare metal), and expect longer on a slow connection or a slower computer. If it stops with `package_installation_invalid`, wait a minute and run the same command again; troubleshooting explains why.

Proposed:

> Expect it to take several minutes. The previous release's public command took 474 seconds (about 8 minutes) once on a test virtual machine; allow more on a slow connection or a slower computer. For this release: <!-- facts:install-seconds -->. If it stops with `package_installation_invalid`, wait a minute and run the same command again; troubleshooting explains why.

### Template import and the study sample

Now:

> To try your own project, place a Git repository below `/var/lib/stateport/imports` and use **Catalog → Import a repository**. On Alpha.21 such a checkout was imported without an ownership fix (not repeated on Alpha.24). If it does not appear, see troubleshooting.

Proposed:

> To try your own project, place a Git repository below `/var/lib/stateport/imports` and use **Catalog → Import a repository**, or give a public repository address with its exact commit. If it does not appear, see troubleshooting.

Now:

> The study sample needs no provider login: everything in it is proposed by a fixed script. Chat replies and coding-agent runs would need a provider connection, and they have not been shown to work. Importing the real StudyState template … from its public GitHub address worked on Alpha.24 (it adds a read-only inspect action, not the study planner); importing ProjectState or any other template from a public Git address was not tested on Alpha.24.

Proposed:

> The study sample needs no provider login. Chat and the agent actions need a model, and you can use OpenCode's free models without an account, after accepting their terms. Importing a template gives you that template's own check and its own actions.

### The keep-alive paragraph

Now: a long paragraph about the triggers on Alpha.24, Alpha.21 and Alpha.20, and the unmeasured reboot.

Proposed:

> **Be aware:** the Windows task that keeps Ubuntu running is registered to start at Windows start-up, at sign-in and every 10 minutes. Whether it keeps StatePort reachable after the last Ubuntu window closes, and what happens after a Windows restart, are not measured yet for this release: <!-- facts:keepalive-result --> and <!-- facts:reboot-result -->. If the local address stops answering, open an Ubuntu window and reload after a few minutes, or sign out of Windows and back in, then reload the page.

### The uninstall bullet

Now:

> **Uninstall:** the command above only installs. The Alpha.24 installer prints options to stop and remove StatePort (your data is kept) and to reinstall it. They passed in a Linux test lab that imitates WSL2 (run on Alpha.22); they were not run on Windows, and this page has no one-line uninstall. The update and removal guide says what is and is not known. Do not run an installer from another release against an Alpha.22 install.

Proposed:

> **Remove it:** `~/.local/state/stateport-install/bin/stateport uninstall` removes StatePort and keeps your data; `~/.local/state/stateport-install/bin/stateport purge` deletes the data as well, after you type a confirmation, and needs your `sudo` password. Both on Windows: <!-- facts:removal-result -->. The update and removal guide has the details. Do not run an installer from another release against a newer install.

### What to include in a report

Now:

> the version (Alpha.24) and the last lines of the installer's output; failures start with `StatePort install:`;

Proposed:

> the version (Alpha.26) and the last lines of the installer's output; failures start with `StatePort install:`;

---

## `releases/index.html`

### Metadata

The meta description, the `og:description` and the JSON-LD `description`
carry the release label. The tool flips them.

### Notice

Now:

> **StatePort is in early alpha. Do not use it for important data.** Use test data and keep your own backups.

Proposed: unchanged.

### Heading

Now:

> Alpha.24 is the current early alpha

Proposed:

> Alpha.26 is the current early alpha

### Release label

Now:

> **Release label.** Alpha.24 is the current public alpha. Its signed release index marks it a qualification candidate; it is not yet qualified. The index also declares rollback unsupported: there is no supported way back to an earlier alpha, and data saved by one alpha may not work in another.

Proposed:

> **Release label.** Alpha.26 is the current public alpha, and it is an early alpha. There is no supported way back to an earlier release: you can move forward to a newer one, and data saved by one release may not be usable in another.

### The paragraph under the release label

Now: the Alpha.24 and Alpha.23 measurements, the 474 second install, the study sample, the GitHub import, the API port, the outbound network, and the Alpha.21 browser walk-through.

Proposed:

> Alpha.26 is installed on Windows 11 with WSL2 and Ubuntu 24.04 from one command. It gives you a web interface, an API, storage and a sandbox on your own machine, and an address that only your computer can reach. It needs no account for anything except the agent actions and the chat, and for those you can use OpenCode's free models after accepting their terms. The measurements for this release are not in yet: <!-- facts:install-seconds -->, <!-- facts:journey-result -->, <!-- facts:reboot-result -->, <!-- facts:memory-mb -->, <!-- facts:disk-gb -->, <!-- facts:upgrade-result -->, <!-- facts:removal-result --> and <!-- facts:import-result -->. The install, the study sample, a service restart, a full WSL restart and an import from GitHub were measured on the previous release in a Windows 11 test virtual machine, which is a virtual machine and not a physical computer.

### Not working yet

Now: the Alpha.21 failures, the keep-alive task, the unmeasured reboot, undo in the browser, and uninstall on Windows.

Proposed:

> **Not working yet.** You cannot go back to an older release. The Decision Log template is not published yet. Chat answers questions and never changes anything. One undo exists, for the last evidence update in the study sample. A backup holds the files of one application, not its history or its conversations. There is no team, no hosted version and no supported way to reach it over a network. The measurements above are not in yet. The full list is on current limitations.

### The availability table

Rows to change, with the wording proposed for each:

| Row | Proposed wording for Alpha.26 |
|---|---|
| Product preview | Available; the video was recorded on an earlier development build, and its &ldquo;stay undoable&rdquo; line does not hold for this release |
| Alpha.26 one-line installer | Available; the measurements are not in yet: <!-- facts:install-seconds -->, <!-- facts:journey-result --> |
| Alpha.24 one-line installer (previous release) | Files remain available. Measured through the public command itself: exit 0 in 474 seconds on a pristine Windows 11 test VM (one attempt); real-Windows and reboot results pending |
| Alpha.23 one-line installer (older release) | Files remain available. Measured through the public command itself: exit 0 in about 9 minutes on a pristine Windows 11 test VM (3 of 4 attempts on these bytes) |
| Study sample loop | Measured on the previous release through the product&rsquo;s own interface: start an activity, review the exact change, approve, reflect, and read the durable result back; state kept after a StatePort service restart and a full WSL distribution restart (7 of 7 checks both times). In the browser: measured on Alpha.21, not repeated since. For this release: <!-- facts:journey-result --> |
| Reachable after the last WSL window closes | Not measured for this release: <!-- facts:keepalive-result --> |
| Windows reboot survival | Not measured for this release: <!-- facts:reboot-result --> |
| Template import on Windows | Importing the StudyState template from GitHub worked on the previous release (inspected, planned and installed as a new instance). For this release: <!-- facts:import-result --> |
| Backup and restore | A backup archives the files of one application, not its Git history, its conversations, the index of records or the approvals; a restore creates a new application from it. For this release: <!-- facts:backup-result --> |
| Chat replies and agent runs | A model route is needed. Chat answers questions and never changes anything; an agent action works on a copy and hands you a proposal. For this release: <!-- facts:agent-action-result --> |
| Undo and rollback | One undo exists, for the last evidence update in the study sample. Undo for other changes is not built. There is no supported way back to an earlier release, and data saved by one release may not be usable in another |

---

## Placeholders used in this draft

| Placeholder | Page |
|---|---|
| `facts:install-seconds` | index.html, download/index.html, releases/index.html |
| `facts:journey-result` | index.html, download/index.html, releases/index.html |
| `facts:reboot-result` | index.html, download/index.html, releases/index.html |
| `facts:keepalive-result` | download/index.html, releases/index.html |
| `facts:memory-mb` | index.html, download/index.html, releases/index.html |
| `facts:disk-gb` | index.html, download/index.html, releases/index.html |
| `facts:upgrade-result` | download/index.html, releases/index.html |
| `facts:removal-result` | download/index.html, releases/index.html |
| `facts:import-result` | index.html, download/index.html, releases/index.html |
| `facts:backup-result` | releases/index.html |
| `facts:agent-action-result` | releases/index.html |

## Text that must not be edited by hand

| Where | Why |
|---|---|
| The exact status statement in `index.html`, `download/index.html` and `releases/index.html` | `scripts/validate_repo.py` checks this paragraph word for word. The release tool replaces it with the new one together with the release index. |
| The install command and the SHA-256 of `download/install.sh` | The download page must show the fingerprint of the file that is actually published. |
| The `StatePortKeepAlive` task description | The triggers are what the installer registers; they are described again in the docs, and the two must agree. |
