# Prep Academy Knowledge Base

Curated medical knowledge for the Austrian **Kenntnisprüfung (KP)** and medical degree licensing.

---

## Licensing & Degree Recognition

- [Nostrifikation](wiki/nostrifikation.md) — Medical degree recognition in Austria (Stichprobentest, ÄrzteG 1998)
- [Austria Medical Licensing](wiki/sources/austria-medical-licensing.md) — Raw source summary (3 facts about Nostrifikation)

## Source Documents

- [KP Vorbereitung — Amboss Zusammenfassung](wiki/sources/kp-vorbereitung-amboss.md) — 588-page Amboss summary for the KP exam
- [Austria Medical Licensing](wiki/sources/austria-medical-licensing.md) — Recognition of foreign medical degrees

## Medical Specialties (KP Exam Topics)

| Specialty | Page | Key Diseases |
|-----------|------|-------------|
| **Pneumologie** | [→](wiki/pneumologie.md) | Asthma, COPD, Lungenembolie, Pneumonie, Lungenkarzinom, Pleuraerguss |
| **Kardiologie** | [→](wiki/kardiologie.md) | Herzinsuffizienz, KHK, Myokardinfarkt, Rhythmusstörungen, Vitien, Endokarditis, Hypertonie |
| **Gastroenterologie** | [→](wiki/gastroenterologie.md) | GERD, Ulkus, GI-Blutung, CED (M. Crohn, Colitis ulcerosa), Hepatitis, Zirrhose, Pankreatitis |
| **Innere Medizin** | [→](wiki/innere-medizin.md) | Diabetes, Schilddrüse, Niereninsuffizienz, Nebennierenerkrankungen |
| **Neurologie** | [→](wiki/neurologie.md) | Schlaganfall, Epilepsie, Parkinson, MS, Demenz, Meningitis |
| **Notfallmedizin** | [→](wiki/notfallmedizin.md) | ABCDE, Schock, Reanimation (ALS), Anaphylaxie, akute Dyspnoe |
| **Chirurgie** | [→](wiki/chirurgie.md) | Akutes Abdomen, Appendizitis, Ileus, Hernien, Wundheilung |
| **Orthopädie** | [→](wiki/orthopaedie.md) | Frakturen, Arthrose, Osteoporose, Rückenschmerz, Bandscheibenvorfall |
| **Pharmakologie** | [→](wiki/pharmakologie.md) | Vegetativum, Kardiaka, Antibiotika, Analgetika, Lokalanästhetika |
| **Pädiatrie** | [→](wiki/paediatrie.md) | Impfungen, Entwicklung, Fieberkrampf, Pseudokrupp, angeborene Herzfehler |
| **Psychiatrie** | [→](wiki/psychiatrie.md) | Depression, Schizophrenie, Angststörungen, Sucht, Psychopharmaka |
| **Gynäkologie** | [→](wiki/gynaekologie.md) | Schwangerschaft, gyn. Tumoren (Mamma, Zervix, Ovar, Endometrium), Kontrazeption |
| **Urologie** | [→](wiki/urologie.md) | Nierensteine, Harnwegsinfekte, Prostatakarzinom, Hodenkarzinom |
| **HNO** | [→](wiki/hno.md) | Sinusitis, Tonsillitis, Hörstörungen, Schwindel, Epistaxis |
| **Dermatologie** | [→](wiki/dermatologie.md) | Ekzeme, Psoriasis, Hauttumoren (Melanom, Basaliom, Spinaliom) |
| **Anästhesie** | [→](wiki/anaesthesie.md) | Narkose, Beatmung, TIVA, Regionalanästhesie, ASA-Klassifikation |
| **Infektiologie** | [→](wiki/infektiologie.md) | HIV, Tuberkulose, Sepsis, MRE (MRSA, VRE, ESBL, CRE) |
| **Hygiene** | [→](wiki/hygiene.md) | Händehygiene, nosokomiale Infektionen, Desinfektion, Isolation |
| **Rechtsmedizin** | [→](wiki/rechtsmedizin.md) | Todesfeststellung, Obduktion, Spurensicherung, Toxikologie |

## Cross-Cutting Concepts

| Concept | Page | Key Topics |
|---------|------|------------|
| **Diagnostik** | [→](wiki/diagnostik.md) | Röntgen, CT, MRT, Sonographie, EKG, Labor, BGA |
| **Biostatistik** | [→](wiki/biostatistik.md) | Studiendesign, Sensitivität/Spezifität, PPV/NPV, p-Werte, KI, Bias |
| **Klinische Untersuchung** | [→](wiki/klinische-untersuchung.md) | Inspektion, Palpation, Perkussion, Auskultation, neurologischer Status |
| **Prävention** | [→](wiki/praevention.md) | Vorsorge, Impfungen (Erwachsene), Umweltmedizin, Präventionsstufen |

## Structure

```
knowledge/
├── AGENTS.md         — KB maintenance rules
├── index.md          — ← you are here
├── roadmap.md        — Future architecture migration plan
├── gaps.md           — Missing content tracking
├── raw/              — Source documents (imported via frontend)
├── wiki/             — Structured knowledge pages (flat, ~25 pages)
│   ├── sources/      — Source summaries
│   └── *.md          — Specialty + concept pages
```
