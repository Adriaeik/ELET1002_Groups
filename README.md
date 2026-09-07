
# ELET1002 Group Task Allocator

Dette Python-skriptet fordeler oppgåver mellom grupper basert på Canvas Quiz-svar og genererer PDF-ar med oversikt over resultatet.

## TL;DR - ihvertfall les ditta

1. Last ned Quiz-rapport frå Canvas med **Student Analysis Report** (CSV-format)
2. Plasser CSV-fila i mappe `TicksSheet`.
3. Køyr skriptet og oppgi SLT-nummeret

## Nedlasting frå Canvas

1. Gå til quizen i Canvas
2. Klikk på **Quiz Statistics** → **Student Analysis**
3. Last ned CSV-fila
4. Legg fila i `TicksSheet/`-mappa

## Format på Canvas-rapporten

Skriptet kjenner att begge formata automatisk:

| | Gammalt format | Nytt format |
| --- | --- | --- |
| Gruppe | eige quiz-spørsmål (`Hvilken SLT-gruppe tilhører du?`) | Canvas-seksjonen, t.d. `TET4100-26H-9 :: 5 - The Mighty Power Nappers` |
| Oppgåvespørsmål | `... presentere oppgave 1` | `... present Task #1` |
| Svar | `Ja` / `Nei` | `True` / `False` |

Ligg det fleire CSV-ar i `TicksSheet/`, blir den nyaste fila brukt.

## Funksjonar

### 1. Oppgåvefordeling

* Fordeler oppgåver mellom subgrupper basert på kven som har svart **Ja** på kvar oppgåve
* Prioriterer rettferdig fordeling slik at kvar oppgåve blir tildelt éin kvalifisert person per subgruppe
* Ingen får ei oppgåve dei ikkje har svart Ja på
* Handterer automatisk fleire forsøk (brukar siste gyldige forsøk)

### 2. Subgruppebalansering

* Studentar blir fordelte i subgrupper (mål: ~6 per subgruppe, maks 4 subgrupper)
* Alle deltakarar utan oppgåve blir fordelte jamnt mellom subgruppene
* Dermed får alle subgrupper tilnærma lik storleik

### 3. PDF-generering

Skriptet lagar følgjande struktur:

```
SLT/
├── SLT<nr>.zip              # Alle PDF-ane under samla i éi fil
└── SLT<nr>/
    ├── gruppe1/
    │   ├── TaskAllocation.pdf   # Alle subgrupper med oppgåvefordeling
    │   └── GroupOverview.pdf    # Alle subgrupper, berre medlemsliste
    ├── gruppe2/
    │   ├── TaskAllocation.pdf
    │   └── GroupOverview.pdf
    ...
    └── gruppe10/
        ├── TaskAllocation.pdf
        └── GroupOverview.pdf
```

* `TaskAllocation.pdf` – viser kven som har fått kva oppgåve for alle subgrupper
* `GroupOverview.pdf` – viser berre medlemmar, kan delast utan å avsløre oppgåver
* `SLT<nr>.zip` – alle PDF-ane frå alle gruppene, klar til opplasting/deling.

## Krav

### Avhengigheiter

* `pandas` – for å lese og handtere CSV-data
* `reportlab` – for å generere PDF-filene

Installer med:

```bash
pip install -r requirements.txt
```

## Bruk

1. Legg CSV-fila frå Canvas i mappa `TicksSheet/`
2. Køyr skriptet:

```bash
python TaskAllocator.py
```

3. Oppgi SLT-nummeret når du blir spurt
4. PDF-ar blir lagra i `SLT<nr>/`-mappa

## Eksempel

```
$ python TaskAllocator.py
Lastar inn: TicksSheet/Quiz_Student_Analysis_Report.csv
Fann 6 oppgåver: [1, 2, 3, 4, 5, 6]
Fann 10 grupper i data: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

Kva SLT-nummer er dette? 1

Prosesserer gruppe 1: 5 studentar → 1 subgruppe(r)
Prosesserer gruppe 2: 7 studentar → 1 subgruppe(r)
Prosesserer gruppe 3: 6 studentar → 1 subgruppe(r)
Prosesserer gruppe 4: 2 studentar → 1 subgruppe(r)
Prosesserer gruppe 5: 8 studentar → 1 subgruppe(r)
...

Ferdig! Grupper lagra i SLT/SLT1/
Zip med 16 PDF-ar: SLT/SLT1.zip
```

## Testar

Regresjonstestane køyrer mot anonymiserte fixturar i `tests/fixtures/` og
dekkjer begge CSV-formata. Dei køyrer automatisk i GitHub Actions ved push og
pull request.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Testane vaktar mellom anna at:

* begge formata blir kjende att, og at gruppa blir lesen frå rett stad
* **siste forsøk alltid gjeld** - kryssar nokon av og so vekk igjen, tel det siste
* ingen får ei oppgåve dei ikkje har kryssa av for
* ingen hamnar i to subgrupper samstundes
* ingen studentar forsvinn undervegs
* zipen får med alle PDF-ane, og ikkje seg sjølv

Ein eigen CI-jobb feilar om CSV-, Excel- eller PDF-filer blir sjekka inn
utanfor `tests/fixtures/`, slik at studentdata ikkje hamnar i repoet.

## Feilsøking

**"Ingen CSV-filer funnet"**

* Sjekk at du har laga `TicksSheet/`-mappa og lagt CSV-fila der

**"Fann ikkje gruppekolonna"**

* Sjekk at quizen har eit spørsmål om SLT-gruppe (gammalt format), eller at
  `section`-kolonna har gruppenummer etter `::` (nytt format)

**"Fann ingen oppgåvekolonner i CSV"**

* Sjekk at spørsmåla heiter `... presentere oppgave <nr>` eller `... present Task #<nr>`
