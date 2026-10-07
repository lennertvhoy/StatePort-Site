# LinkedIn-post, Nederlands (definitief)

> Voeg `launch/demo/stateport-demo-19s.mp4` toe (19 s, echte productinterface). Post bij voorkeur di-do tussen 08:00 en 10:00.

---

Ik verloor steeds werk zodra een AI-chat ophield: het plan, de beslissingen, de redenen erachter. Alles zit in één chatvenster, en dan is het weg.

Daarom bouw ik StatePort. Het idee is dat je project of studieplan op je eigen computer staat, met een bewijs (receipt) van elke wijziging die je goedkeurt, zodat een nieuwe sessie begint bij wat er echt staat. Vandaag werkt dat alleen in het ingebouwde studievoorbeeld: een activiteit bekijken, een wijziging goedkeuren, een reflectie bewaren.

Het is een vroege alpha, dus dit is precies waar het staat. Het publieke één-regel-commando installeerde Alpha.23 op een schone Windows 11 + WSL2 (Ubuntu 24.04)-testmachine en eindigde met exit 0 in ongeveer 9 minuten (3 van 4 pogingen op deze bytes; de 4e crashte in de optionele keep-alive-registratie door een trage PowerShell-aanroep — een fix ligt klaar maar is nog niet uitgebracht). Het ingebouwde studievoorbeeld werkte end-to-end: activiteit starten, de exacte wijziging bekijken, goedkeuren, receipt, reflectie, met het resultaat teruggelezen van schijf — en het overleefde een herstart van StatePort én een volledige WSL-herstart. Twee gemeten punten blijven open: het installatieplan noemt één API-poort terwijl de draaiende API op een andere antwoordt (het geprinte adres is het juiste), en het importeren van de StudyState-template vanaf GitHub faalt omdat de containers van het product op een stock WSL2 geen hostnamen kunnen oplossen. Een Windows-herstart is niet getest en verwijderen is op Windows niet uitgevoerd. Zet er dus niets belangrijks in.

Werk je op Windows 11 met WSL2 en wil je het proberen? Ik hoor graag waar de installatie stukloopt:
https://lennertvhoy.github.io/StatePort-Site/

Wat zou jij willen dat een AI voor je onthoudt tussen sessies?
