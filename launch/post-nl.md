# LinkedIn-post, Nederlands (definitief)

> Voeg `launch/demo/stateport-demo-19s.mp4` toe (19 s, echte productinterface). Post bij voorkeur di-do tussen 08:00 en 10:00.

---

Ik verloor steeds werk zodra een AI-chat ophield: het plan, de beslissingen, de redenen erachter. Alles zit in één chatvenster, en dan is het weg.

Daarom bouw ik StatePort. Het idee is dat je project of studieplan op je eigen computer staat, met een bewijs (receipt) van elke wijziging die je goedkeurt, zodat een nieuwe sessie begint bij wat er echt staat. Vandaag werkt dat alleen in het ingebouwde studievoorbeeld: een activiteit bekijken, een wijziging goedkeuren, een reflectie bewaren.

Het is een vroege alpha, dus dit is precies waar het staat. Het publieke één-regel-commando installeerde Alpha.24 op een schone Windows 11 + WSL2 (Ubuntu 24.04)-testmachine (een KVM-gast, geen echte hardware) en eindigde met exit 0 in 474 seconden, bij één poging. Het studievoorbeeld liep end-to-end: een activiteit starten, de exacte wijziging bekijken, goedkeuren, receipt, reflectie, met het resultaat teruggelezen van schijf — en het overleefde een herstart van StatePort en een volledige WSL-herstart. Het importeren van de StudyState-template van GitHub werkt nu binnen StatePort (op Alpha.23 mislukte het omdat de containers geen hostnamen konden oplossen); de webservice heeft nu uitgaande internettoegang via een eigen netwerk, terwijl de API en de worker geïsoleerd blijven. Het installatieplan en de draaiende API zijn het nu eens over de poort. Niet gemeten op Alpha.24: een Windows-herstart, verwijderen op Windows, ProjectState en een derde template, een volledige UI-audit, resourcegebruik. Zet er dus niets belangrijks in.

Werk je op Windows 11 met WSL2 en wil je het proberen? Ik hoor graag waar de installatie stukloopt:
https://lennertvhoy.github.io/StatePort-Site/

Wat zou jij willen dat een AI voor je onthoudt tussen sessies?
