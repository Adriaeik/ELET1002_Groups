# Testfixturar

Anonymiserte Canvas-rapportar som regresjonstestane køyrer mot.

| Fil | Format |
| --- | --- |
| `new_format.csv` | Haust 26 og seinare - gruppe i `section`, engelske spørsmål, `True`/`False` |
| `old_format.csv` | Vår 26 - eige gruppespørsmål i quizen, norske spørsmål, `Ja`/`Nei` |

## Anonymisering

Namn og student-id-ar er bytta ut med syntetiske verdiar, og radrekkjefølgja er
stokka. Alle id-ar startar på 900000 - CI feilar om ein id under den grensa dukkar
opp, sidan det tyder på at ekte data har snike seg inn.

Alt anna er bevart nøyaktig slik Canvas eksporterte det, fordi det er nettopp
detaljane som har brote koden før:

* kolonnenamn over fleire linjer (`... present Task #1 ?\nRemark: ...`)
* seksjonsstrengar med gruppa etter `::`, i vilkårleg rekkjefølgje
* studentar med fleire forsøk, inkludert éin som kryssa av og so kryssa vekk igjen
* ein student som berre står i emneseksjonen, utan SLT-gruppe
* namn med æ/ø/å

**Legg aldri ekte Canvas-eksportar her.** Dei høyrer heime i `TicksSheet/`, som
er gitignorert.
