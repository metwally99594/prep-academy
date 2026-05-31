---
type: concept
title: Biostatistik & Evidenzbasierte Medizin
status: stable
last_reviewed: 2026-05-31
sources: []
tags: [type/concept, exam/kp, status/stable]
related:
- '[[diagnostik]]'
- '[[pharmakologie]]'
- '[[hygiene]]'
---

# Biostatistik & Evidenzbasierte Medizin

## Studiendesigns

| Typ | Merkmal | Stärke | Schwäche |
|-----|---------|--------|----------|
| **Randomisierte kontrollierte Studie (RCT)** | Goldstandard, Patienten werden randomisiert der Intervention/Kontrolle zugeteilt | Minimiert Confounding, kausale Aussage | Teuer, ethische Limitationen, oft selektive Patienten |
| **Kohortenstudie** | Prospektiv, exponiert vs. nicht exponiert, Nachverfolgung über Zeit | Seltene Expositionen, mehrere Endpunkte | Teuer, lange Dauer, Loss to follow-up |
| **Fall-Kontroll-Studie** | Retrospektiv, Kranke vs. Gesunde → Exposition bestimmen | Seltene Erkrankungen, schnell, kostengünstig | Recall Bias, Confounder |
| **Querschnittsstudie** | Prävalenz zu einem Zeitpunkt | Prävalenzbestimmung, Hypothesengenerierend | Keine Kausalität |
| **Systematischer Review** | Zusammenfassung aller Studien zu einer Fragestellung | Höchste Evidenzstufe | Qualität der eingeschlossenen Studien |
| **Metaanalyse** | Statistische Zusammenfassung (gepoolte Effektschätzer) | Größere statistische Power, Präzision | Heterogenität der Studien |

## Diagnostische Tests

| Test positiv | Krankheit vorhanden | Krankheit nicht vorhanden |
|-------------|-------------------|--------------------------|
| **Test negativ** | Richtig positiv (RP) | Falsch positiv (FP) |
| | Falsch negativ (FN) | Richtig negativ (RN) |

- **Sensitivität** = RP / (RP + FN) — Wahrscheinlichkeit, dass ein Kranker positiv getestet wird (Wahrscheinlichkeit, Krankheit zu erkennen)
- **Spezifität** = RN / (RN + FP) — Wahrscheinlichkeit, dass ein Gesunder negativ getestet wird (Regel der Krankheit "spezifisch")
- **Positiver Vorhersagewert (PPV)** = RP / (RP + FP) — Wahrscheinlichkeit, dass eine positive Testperson krank ist (abhängig von Prävalenz)
- **Negativer Vorhersagewert (NPV)** = RN / (RN + FN) — Wahrscheinlichkeit, dass eine negative Testperson gesund ist
- **Prävalenz** = Erkrankte / Gesamtpopulation

**Merksatz**: "SnNouts" (hohe Sensitivität → negativer Test schließt Erkrankung aus, Sn=Negative out); "SpPins" (hohe Spezifität → positiver Test schließt Erkrankung ein, Sp=Positive in)

**Likelihood Ratio (LR)**:
- LR+ = Sensitivität / (1 - Spezifität); je höher, desto besser zum Bestätigen
- LR- = (1 - Sensitivität) / Spezifität; je niedriger, desto besser zum Ausschließen

## Statistische Grundbegriffe

- **p-Wert**: Wahrscheinlichkeit, dass der beobachtete Effekt (oder ein extremerer) allein durch Zufall auftritt, wenn die Nullhypothese wahr ist; Signifikanzniveau α = 0,05 (konventionell)
- **Konfidenzintervall (KI)**: Bereich, der mit einer Wahrscheinlichkeit von 95% den wahren Populationsparameter enthält; wenn KI die 1 (Odds Ratio/Relatives Risiko) nicht einschließt → signifikant
- **Relatives Risiko (RR)** = Inzidenz in exponierter Gruppe / Inzidenz in nicht-exponierter Gruppe
- **Odds Ratio (OR)** = (RP × RN) / (FN × FP) — Annäherung an RR bei seltenen Erkrankungen
- **Number Needed to Treat (NNT)** = 1 / Absolute Risikoreduktion (ARR); Anzahl der Patienten, die behandelt werden müssen, um einen Endpunkt zu verhindern
- **Number Needed to Harm (NNH)** = 1 / Absolute Risikoerhöhung (ARI); Anzahl der Patienten, bei deren Behandlung ein schädliches Ereignis auftritt

**Fehlerarten**:
| Fehler | Beschreibung | Wahrscheinlichkeit |
|--------|-------------|-------------------|
| **α-Fehler (Typ I)** | Nullhypothese fälschlicherweise abgelehnt → falsch positiv | α (Signifikanzniveau, z.B. 0,05) |
| **β-Fehler (Typ II)** | Nullhypothese fälschlicherweise beibehalten → falsch negativ | β |

- **Power** = 1 − β; Wahrscheinlichkeit, einen Effekt zu erkennen, wenn er existiert (≥80% angestrebt)

## Klinische Studien (Bias)

| Bias | Beschreibung | Vermeidung |
|------|-------------|------------|
| **Selektionsbias** | Systematische Unterschiede zwischen Gruppen | Randomisierung |
| **Performancebias** | Unterschiedliche Behandlung außerhalb der Intervention (z.B. durch Wissen der Beteiligten) | Verblindung (doppelblind) |
| **Detectionbias** | Unterschiedliche Erfassung der Endpunkte | Verblindung der Endpunkterhebung |
| **Attritionbias** | Unterschiedlicher Studienabbruch zwischen Gruppen | Intention-to-treat-Analyse |
| **Recall Bias** | Erinnerungsverzerrung (Fall-Kontroll-Studien) | Prospektive Datenerhebung |

## Related Pages

- [[diagnostik|Diagnostik]] — Sensitivität/Spezifität von bildgebenden Verfahren, prädiktive Werte
- [[pharmakologie|Pharmakologie]] — NNT/NNH in klinischen Studien, Evidenz für Medikamentenwirksamkeit
- [[hygiene|Hygiene]] — Studien zur Effektivität von Hygienemaßnahmen
