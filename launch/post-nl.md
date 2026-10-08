# LinkedIn-post, Nederlands (definitief)

> Voeg `launch/demo/stateport-demo-19s.mp4` toe (19 s, echte productinterface). Post bij voorkeur di-do tussen 08:00 en 10:00.

---

Ik verloor steeds werk zodra een AI-chat ophield: het plan, de beslissingen, de redenen erachter. Alles zit in één chatvenster, en dan is het weg.

Daarom bouw ik StatePort. Het idee is dat je project of studieplan op je eigen computer staat, met een bewijs (receipt) van elke wijziging die je goedkeurt, zodat een nieuwe sessie begint bij wat er echt staat. Vandaag werkt dat alleen in het ingebouwde studievoorbeeld: een activiteit bekijken, een wijziging goedkeuren, een reflectie bewaren.

Het is een vroege alpha, dus dit is precies waar het staat. Alpha.24 installeert en slaagt in een schone Windows 11 + WSL2 (Ubuntu 24.04)-test-VM; resultaten op echte Windows en na een herstart zijn nog open. Op Alpha.24 heb ik tot nu toe één installatie vanaf een lokale kopie van de ondertekende bestanden gemeten (gezond, een tweede run veranderde niets); het publieke één-regel-commando, het studievoorbeeld, herstarts en de GitHub-template-import heb ik daarop nog niet gemeten. Op de vorige release, Alpha.23, installeerde het publieke commando op een schone test-VM en eindigde met exit 0 in ongeveer 9 minuten (3 van 4 pogingen), liep het studievoorbeeld end-to-end en overleefde het een service-herstart en een volledige WSL-herstart, noemde het installatieplan één API-poort terwijl de draaiende API op een andere antwoordde, en mislukte het importeren van de StudyState-template van GitHub omdat de containers geen hostnamen konden oplossen. Alpha.24 bevat wijzigingen daarvoor, die nog gecontroleerd worden. Een Windows-herstart is niet getest en verwijderen is op Windows niet uitgevoerd. Zet er dus niets belangrijks in.

Werk je op Windows 11 met WSL2 en wil je het proberen? Ik hoor graag waar de installatie stukloopt:
https://lennertvhoy.github.io/StatePort-Site/

Wat zou jij willen dat een AI voor je onthoudt tussen sessies?
