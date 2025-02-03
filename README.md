# ELET1002 Group Task Allocator

Dette Python-skriptet fordeler oppgåver mellom grupper og genererer ein godt formatert PDF med oppsummering av resultatet.

---

## Viktig!
1. Last ned data frå Blackboard med følgjande innstillingar (sjå bilete):
   - Skiljeteikn: **Komma**
   - Format på resultat: **Etter brukar**
   - Forsøk: **Berre gyldige forsøk**

2. Dersom Blackboard ikkje er på nynorsk:
   - Endre `full_name_col` (linje 20) frå `"Fullt namn"` til `"Fullt navn"`.

3. Dersom fila er på engelsk:
   - Endre `full_name_col` til `"Full name"`.
   - Endre `answers` (linje 21) til `[col for col in data.columns if col.lower().startswith("answer")]`.
   - Endre `"Sann"` (linje 32) til `"True"`.

---

## Funksjonar

1. **Oppgåvefordeling**:
   - Fordeler oppgåver blant grupper basert på tilgjengeligheit.
   - Sikrar jamn fordeling der ingen gruppe har meir enn éi oppgåve meir enn dei andre.

2. **Gruppebalansering**:
   - Fordeler resterande deltakarar jevnt til gruppene.

3. **PDF-generering**:
   - Genererer ein PDF som oppsummerer oppgåvefordeling og gruppemedlemskap.

---

## Krav

### Avhengigheiter
- `pandas`: For å handtere datafilene.
- `fpdf`: For å generere PDF-rapporten.

---

## Bruk

1. Legg CSV-fila i prosjektmappa.
2. Kjør skriptet:
   ```bash
   python TaskAllocator.py
   ```
3. Oppgi ønskja tal på grupper når du blir spurt.
4. PDF-en `GroupAllocation.pdf` blir lagra i mappa.

---

## Input-format

Fila må innehalde følgjande kolonnar:
1. Ein kolonne med namn (`Fullt namn`, `Fullt navn`, eller `Full name`).
2. Kolonnar for oppgåvesvar (`Svar 1`, `Answer 1`, osv.) med verdiar `Sann`/`Usann` eller `True`/`False`.

Eksempel:

| Fullt namn        | Svar 1  | Svar 2  | Svar 3  |
|-------------------|---------|---------|---------|
| Ola Nordmann      | Sann    | Usann   | Sann    |
| Kari Nordmann     | Sann    | Sann    | Usann   |
