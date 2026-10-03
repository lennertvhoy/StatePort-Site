# LinkedIn-post, Nederlands (definitief)

> Voeg `launch/demo/stateport-demo-19s.mp4` toe (19 s, echte productinterface). Post bij voorkeur di-do tussen 08:00 en 10:00.

---

Ik verloor steeds werk zodra een AI-chat ophield: het plan, de beslissingen, de redenen erachter. Alles zit in één chatvenster, en dan is het weg.

Daarom bouw ik StatePort. Het idee is dat je project of studieplan op je eigen computer staat, met een bewijs (receipt) van elke wijziging die je goedkeurt, zodat een nieuwe sessie begint bij wat er echt staat. Vandaag werkt dat alleen in het ingebouwde studievoorbeeld: een activiteit bekijken, een wijziging goedkeuren, een reflectie bewaren.

Het is een vroege alpha, dus dit is precies waar het staat. De Alpha.22-installer voor Windows 11 + WSL2 (Ubuntu 24.04) installeert en slaagt in een schone test-VM; resultaten op echte Windows en na een herstart zijn nog open. Die test gebruikte een lokale kopie van de ondertekende bestanden, niet de publieke one-liner, en de browserdoorloop is op Alpha.22 nog niet herhaald. Op Alpha.21 werkte het studievoorbeeld in de browser: je keurt de exacte wijziging goed, bewaart een reflectie, krijgt een receipt, en na een herlading staat alles er nog. Chatantwoorden, coding-agent-runs en container-werkruimtes werkten op Alpha.21 niet en zijn niet opnieuw gemeten. Een Windows-herstart is niet getest en verwijderen is op Windows niet uitgevoerd. Zet er dus niets belangrijks in.

Werk je op Windows 11 met WSL2 en wil je het proberen? Ik hoor graag waar de installatie stukloopt:
https://lennertvhoy.github.io/StatePort-Site/

Wat zou jij willen dat een AI voor je onthoudt tussen sessies?
