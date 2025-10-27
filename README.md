# ELET1002 Group Task Allocator

Dette Python-skriptet fordeler oppgåver mellom grupper og genererer to PDF-ar med oversikt over resultatet.
## Fordi ingen har tolmodighet - ihvertfall les ditta

Lag ein mappe kalla `TicksSheet` og plasser `csv` fila lasta ned frå blackboard i den. 
---

## Viktig!

1. Last ned data frå Blackboard med følgjande innstillingar (sjå bilete):

   * Skiljeteikn: **Komma**
   * Format på resultat: **Etter brukar**
   * Forsøk: **Berre gyldige forsøk**

2. Dersom Blackboard ikkje er på nynorsk:

   * Endre `full_name_col` (linje 20) frå `"Fullt namn"` til `"Fullt navn"`.

3. Dersom fila er på engelsk:

   * Endre `full_name_col` til `"Full name"`.
   * Endre `answers` (linje 21) til

     ```python
     [col for col in data.columns if col.lower().startswith("answer")]
     ```
   * Endre `"Sann"` (linje 32) til `"True"`.

---

## Funksjonar

1. **Oppgåvefordeling**

   * Fordeler oppgåver mellom grupper basert på kven som har svart *Sann* på kvar oppgåve.
   * Prioriterer rettferdig fordeling slik at kvar oppgåve blir tildelt éin kvalifisert person per gruppe (der det er mogleg).
   * Ingen får ei oppgåve dei ikkje har svart *Sann* på.

2. **Gruppebalansering (oppdatert)**

   * Alle deltakarar utan oppgåve blir no fordelte **jamnt** mellom gruppene.
   * Skriptet reknar automatisk ut total gruppestorleik (oppgåvepersonar + vanlege medlemmar) og legg nye deltakarar i den minste gruppa først.
   * Dermed får alle grupper tilnærma lik storleik uansett kor mange oppgåver som blei tildelt.

3. **PDF-generering (utvida)**
   Skriptet lagar no to ulike PDF-ar:

   * `GroupAllocation.pdf` – viser full oversikt over kven som har fått kva oppgåve.
   * `GroupOverview.pdf` – viser berre gruppemedlemmane, **utan å avsløre oppgåvefordeling**.
     Denne kan delast med studentane utan å røpe kven som presenterer.

---

## Krav

### Avhengigheiter

* `pandas` – for å lese og handtere CSV-data.
* `fpdf` – for å generere PDF-filene.

Installer med:

```bash
pip install pandas fpdf
```

---

## Bruk

1. Legg CSV-fila frå Blackboard i mappa `TicksSheet/`.
2. Kjør skriptet:

   ```bash
   python TaskAllocator.py
   ```
3. Oppgi ønskja tal på grupper når du blir spurt.
4. To PDF-ar blir lagra:

   * `GroupAllocation.pdf` (full versjon)
   * `GroupOverview.pdf` (anonym versjon)

---

## Input-format

Fila må innehalde:

1. Éin kolonne med namn (`Fullt namn`, `Fullt navn`, eller `Full name`).
2. Éi eller fleire kolonnar med oppgåvesvar (`Svar 1`, `Answer 1`, osv.) med verdiar `Sann`/`Usann` eller `True`/`False`.

Eksempel:

| Fullt namn    | Svar 1 | Svar 2 | Svar 3 |
| ------------- | ------ | ------ | ------ |
| Ola Nordmann  | Sann   | Usann  | Sann   |
| Kari Nordmann | Sann   | Sann   | Usann  |

