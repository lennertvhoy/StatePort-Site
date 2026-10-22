# StatePort 0.1.0-alpha.26 WSL2 public-test candidate

This candidate requires agent-owned installed qualification before product acceptance. It packages the exact release-locked runtime inputs recorded by the candidate build and scan evidence. A real Windows 11, WSL2, and Ubuntu 24.04 clean-install receipt does not yet exist.

What this source adds since the previous public release (implementation, not measured claims; measured results are published on the release status page):

- Applications from templates: import ProjectState_Template, StudyState_Template or any public Git repository that follows the template contract by its HTTPS address, at a branch, tag, commit or the default branch.
- Template actions: checks run on this machine and change nothing; agent actions run in a sandbox on a copy and return a file-change proposal that you apply (one Git commit) or reject.
- Models: with your consent StatePort measures OpenCode's free models on its own practice tasks and routes agent actions and chat to a measured model; it names OpenCode's free usage limit when that refuses a request.
- Chat reads the files a template declares for it and never runs tools.
- Backup and restore for every application, including template copies; a restore always creates a new application.
- Installer: runs from your home folder, waits for Ubuntu's automatic updates instead of failing, pulls only the images the installed services run, and checks service health every five minutes.
- The bundled OpenCode is 1.19.3; the agent sandbox's network proxy admits only TLS for the allowlisted provider hosts.

These implementation claims do not transfer qualification from earlier release bytes.
