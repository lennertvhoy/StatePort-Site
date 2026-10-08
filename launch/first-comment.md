# First comment — pin it right after posting (EN)

StatePort — AI-assisted work saved in files on your own computer: https://lennertvhoy.github.io/StatePort-Site/

Install on Windows 11 + WSL2 (Ubuntu 24.04): open Ubuntu in WSL2 and run
`bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh)`
The public one-line command installed Alpha.24 on a pristine Windows 11 test VM in 474 seconds (one attempt); the study sample works end to end and its data survives StatePort and WSL restarts, and importing the StudyState template from GitHub works. Real-Windows and reboot results are pending. If it stops with `package_installation_invalid` (a check that races Ubuntu's background updates; it stopped one of three Alpha.21 installs), wait a minute and run the same command again.

Known limits, stated plainly: https://lennertvhoy.github.io/StatePort-Site/releases/
Verify the installer bytes yourself: `curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sha256sum` → 4c7499e60b82fded33672dfd472fea87bca8ea96b74a579affc1681af10181fd (also shown on the download page).

Feedback I'd genuinely love:
1. Does the one-line install run cleanly on your Windows 11 + WSL2 machine — and where does it stop if not?
2. Does the known-limits story read honest and clear, or as overclaiming?
3. Which durable-AI workflow should StatePort take on next, after StudyState?

Bugs and reports: https://github.com/lennertvhoy/StatePort-Site/issues

---

# Eerste reactie (NL) — vastpinnen na de Nederlandse post

StatePort — AI-ondersteund werk, bewaard in bestanden op je eigen computer: https://lennertvhoy.github.io/StatePort-Site/

Installeren op Windows 11 + WSL2 (Ubuntu 24.04): open Ubuntu in WSL2 en draai
`bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh)`
Het publieke één-regel-commando installeerde Alpha.24 op een schone Windows 11-test-VM in 474 seconden (één poging); het studievoorbeeld werkt end-to-end en zijn data overleeft StatePort- en WSL-herstarts, en het importeren van de StudyState-template van GitHub werkt. Resultaten op echte Windows en na een herstart zijn nog open. Stopt hij met `package_installation_invalid` (een controle die racet met de achtergrondupdates van Ubuntu; bij Alpha.21 stopte dit één van de drie installaties), wacht dan een minuut en voer dezelfde opdracht opnieuw uit.

Bekende grenzen, eerlijk verwoord: https://lennertvhoy.github.io/StatePort-Site/releases/
Controleer de installer-bytes zelf: `curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sha256sum` → 4c7499e60b82fded33672dfd472fea87bca8ea96b74a579affc1681af10181fd (staat ook op de downloadpagina).

Feedback die ik echt wil:
1. Draait de one-line install netjes op jouw Windows 11 + WSL2-machine — en waar stopt hij als dat niet zo is?
2. Leest het verhaal over bekende grenzen eerlijk en duidelijk, of als overclaiming?
3. Welke duurzame AI-workflow moet StatePort na StudyState oppakken?

Bugs en meldingen: https://github.com/lennertvhoy/StatePort-Site/issues
