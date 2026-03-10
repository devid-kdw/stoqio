# WMS — Project Overview

**Verzija**: v1 (restart)  
**Datum**: 2026-03  
**Vlasnik**: Stefan  

---

## Što je projekt

Univerzalni **Warehouse Management System (WMS)** građen na iskustvu iz stvarne produkcijske okoline. Namijenjen malim i srednjim proizvodnim pogonima koji trebaju digitalnu kontrolu skladišta bez skupih ERP rješenja.

## Biznis model

- **"Software + Hardware" paket**: kupac dobije Raspberry Pi s preinstaliranim softwareom + on-site postavljanje
- **Target kupci**: mala i srednja poduzeća s fizičkim skladištem (proizvodnja, distribucija, servis)
- **Prva implementacija**: interna implementacija u firmi vlasnika projekta — validacija u produkciji
- **Dugoročno**: komercijalizacija kao konfigurabilan WMS za različite industrije

---

## Deployment arhitektura

```
[Raspberry Pi — server]
         |
    Local network (WiFi/LAN)
         |
┌────────┴────────┬──────────────┬──────────────┐
[Terminal 1]  [Terminal 2]  [Terminal 3] ... [do 20]
  (browser)    (browser)     (browser)
  tablet/PC    tablet/PC     tablet/PC
```

- **Pi** pokreće Flask backend + PostgreSQL + React web app
- **Terminali** su bilo koji uređaj s browserom — tablet, PC, touch screen
- **Nema instalacije** na terminalima — sve preko browsera na lokalnoj mreži
- **Update** = jednom na Pi-u, svi terminali odmah vide novu verziju
- **Jedan Pi = jedno skladište / jedna lokacija**

---

## Tech stack

| Sloj | Tehnologija | Napomena |
|------|-------------|----------|
| Backend | Python / Flask | Zadržano iz v1 |
| Baza | PostgreSQL | Zadržano iz v1 |
| Migracije | Alembic | Zadržano iz v1 |
| Frontend | React (web app) | **Promjena**: Electron → web app |
| UI Library | Mantine | Zadržano, dobro funkcionira |
| State/Query | TanStack Query | Zadržano iz v1 |
| Auth | JWT | Zadržano iz v1 |
| i18n | i18next | Zadržano iz v1 |
| Deployment | Raspberry Pi (Linux) | |
| Barkod gen. | python-barcode / qrcode | Generiranje + print |
| Excel export | openpyxl | SAP-kompatibilan export |

> ⚠️ **Ključna promjena vs. prethodna verzija**: Electron je napušten u korist web React app-a.
> Flask backend, PostgreSQL, Alembic, Mantine, TanStack Query — sve ostaje.

---

## Jezici sučelja

| Kod | Jezik | Status |
|-----|-------|--------|
| `hr` | Hrvatski | Default, puna podrška |
| `en` | Engleski | Scaffold u v1 |
| `de` | Njemački | Scaffold u v1 |
| `hu` | Mađarski | Scaffold u v1 |

- Sav kod, API kontrakt, enum vrijednosti — ostaju na engleskom
- UI copy — HR kao default, i18n ključevi za ostale jezike

---

## Hardware prioriteti (investicije)

Sustav mora u potpunosti raditi s ručnim unosom. Hardware je alternativni input, nije preduvjet.

| Prioritet | Hardware | Status |
|-----------|----------|--------|
| 1 | Ručni unos (uvijek) | ✅ Uvijek radi |
| 2 | Barkodovi na bojama + vaga | Investicija, buduće |
| 3 | Barkodovi na potrošnom materijalu | Investicija, buduće |
| 4 | Tablet + skener za 2. smjenu | Investicija, buduće |

---

## Modularnost — MES proširenje

Arhitektura mora biti **modularna** kako bi se u budućnosti mogao dodati **Manufacturing Execution System (MES)** modul bez refaktoriranja WMS jezgre.

**Što MES dijeli s WMS-om**: artikel master data, barkodovi, korisnici, audit trail, lokacije  
**Što MES dodaje**: praćenje komada po fazama, barkod skeniranje po fazama, real-time slika proizvodnje, bottleneck analiza, optimizacija isporuka  

**MES nije u scope v1** — ali svaka arhitekturalna odluka mora ga imati na umu.

---

## ERP / SAP integracija

- Nije live integracija — radi se o **Excel exportu u SAP-kompatibilnom formatu**
- Konfigurabilni export formati (openpyxl već postoji)
- Ne zahtijeva posebnu infrastrukturu, samo dogovor o formatu s upravom
- Sve ostalo (artikli, transakcije, primke) može se exportati i ručno uvući u SAP
