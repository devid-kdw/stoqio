# STOQIO V1 Recap

**Datum recap-a:** 2026-03-17  
**Status:** V1 baseline zatvoren u repozitoriju + post-V1 stabilizacijski popravci evidentirani  
**Opseg:** pregled koda, glavne dokumentacije, handoff traga kroz svih 15 faza i naknadni bugfix hardening

## 1. Kontekst projekta

STOQIO je razvijen kao modularni **WMS za jednu lokaciju**, namijenjen radu preko browsera u lokalnoj mreži, s fokusom na Raspberry Pi deployment i male do srednje proizvodne / skladišne sustave. V1 je od početka vođen kao:

- docs-first projekt
- fazna isporuka u 15 koraka
- strogi handoff protokol između orkestracije, backenda, frontenda i testiranja
- review-driven završavanje svake faze, uključujući follow-up remediacije kad se otkrije stvarni funkcionalni ili ugovorni gap

To znači da V1 nije samo “skupljeni feature set”, nego i dokumentirani proces isporuke s jasnim tragom odluka, verifikacija i naknadnih korekcija.

## 2. Kako je projekt vođen

Projekt je tijekom implementacije imao tri izvora istine:

1. `stoqio_docs/` kao produktna, domenska i arhitekturna baza.
2. `handoff/phase-*` kao operativni dnevnik svake faze.
3. `handoff/decisions/decision-log.md` kao zapis cross-phase odluka i pojašnjenja koja su mijenjala kontrakte ili pravila rada.

Ovaj pristup se pokazao bitnim jer je više faza zatvoreno tek nakon dodatnih review passova, ne samo nakon prvog “done” handoffa. Time je V1 dobio stabilniju bazu bez skrivanja regresija ili spec drift-a.

## 3. Arhitektura i tehnološka baza V1

### Backend

- Flask application factory
- SQLAlchemy modeli + Alembic migracije
- JWT autentikacija i role-based zaštita ruta
- servisni sloj za poslovnu logiku (`approval`, `receiving`, `orders`, `articles`, `employees`, `inventory`, `reports`, `settings`, `barcode`)
- SPA serving iz Flask-a za production build frontenda

### Frontend

- React + Vite + TypeScript
- Mantine UI
- Zustand store za auth i settings state
- centralni RBAC-aware routing
- lazy-loaded stranice po modulima
- HR UI kao default, uz scaffold za `en`, `de`, `hu`

### Podaci i deployment

- početni model pokriva 26 baznih entiteta, a kasnije faze dodaju hardening oko approval override-a, missing article reportova i drugih follow-up detalja
- PostgreSQL je ciljana baza za deployment, a SQLite je korišten i za lokalne verifikacije
- build/deploy skripte postoje i frontend se kopira u `backend/static`

## 4. Što je V1 isporučio

### Temelj sustava

- monorepo skeleton, backend/frontend tooling i build/deploy osnova
- kompletan podatkovni model i migracijska baza
- login, refresh, logout, seed bootstrap i role-based navigacija
- first-run setup za inicijalnu lokaciju i blokadu rada prije inicijalizacije

### Glavni poslovni moduli

- **Draft Entry**: unos izlaza, dnevno grupiranje, shared daily note, batch-aware lookup
- **Approvals**: agregacija po operativnom danu, edit prije odobrenja, approve/reject, stock i surplus logika
- **Receiving**: order-linked i ad-hoc primke, stock povećanje, weighted average price, history
- **Orders**: list/detail, kreiranje i uređivanje, line lifecycle, supplier/article lookups, PDF narudžbenice
- **Warehouse**: list/detail artikala, stock + surplus pregled, reorder status, FEFO batch prikaz, create/edit/deactivate
- **Identifier**: pretraga po article number/opisu/aliasu/barcode-u, missing article queue i resolve flow
- **Employees**: zaposlenici, osobna izdavanja, quota overview, issuance history, stock-aware issuance check/create
- **Inventory Count**: snapshot inventura, autosave brojanja, surplus/shortage obrada i integracija s Approvals
- **Reports**: stock overview, surplus, transaction log, statistike i export
- **Settings**: opće postavke, role display names, UOM, kategorije, kvote, barcode/export postavke, supplieri i korisnici
- **Barcodes & Export**: article i batch barcode PDF flow, export hardening i production-style SPA serving

## 5. Recap po fazama

1. **Phase 01 - Project Setup**  
   Postavljena je jezgra monorepa, Flask app factory, Vite frontend, health endpoint i build/deploy osnova.

2. **Phase 02 - Database Models**  
   Implementiran je kompletan početni model, Alembic scaffold i inicijalna migracija uz PostgreSQL i SQLite provjeru.

3. **Phase 03 - Authentication**  
   Zatvoren je auth flow s seed podacima, RBAC rutiranjem, refresh logikom i sidebar filtriranjem po rolama.

4. **Phase 04 - First-Run Setup**  
   Dodan je setup gate za praznu instalaciju i ADMIN-only inicijalizacija lokacije.

5. **Phase 05 - Draft Entry**  
   Isporučen je prvi operativni workflow unosa izlaza, a zatim je kroz follow-up usklađen s daily-note semantikom i UX pravilima.

6. **Phase 06 - Approvals**  
   Isporučen je approval workflow, zatim očišćen testni kontrakt, override model, bulk-approve transakcijska semantika i legacy `Draft.note` ostatci.

7. **Phase 07 - Receiving**  
   Dodan je receiving engine i privremeni orders lookup/detail sloj potreban da primke rade prije pune Orders faze.

8. **Phase 08 - Orders**  
   Privremeni receiving scaffold zamijenjen je pravim Orders modulom s finalnim API kontraktom i PDF izlazom.

9. **Phase 09 - Warehouse**  
   `articles` namespace je proširen u puni Warehouse modul bez lomljenja lookup kontrakta koji koriste Draft Entry i Receiving.

10. **Phase 10 - Identifier**  
    Isporučena je brza identifikacija artikla i obrada “missing article” queue-a, uz DB-backed deduplikaciju prijava.

11. **Phase 11 - Employees**  
    Dodani su zaposlenici, osobna izdavanja i kvote, a follow-up je ispravio insuficijentni stock branch i dovršio closeout trag.

12. **Phase 12 - Inventory Count**  
    Uvedena je inventura sa snapshot logikom, discrepancy obradom i povezivanjem shortage draftova na postojeći approval pipeline.

13. **Phase 13 - Reports**  
    Dodani su operativni i upravljački izvještaji te export, a follow-up je poravnao export filtre sa stvarno primijenjenim UI stanjem.

14. **Phase 14 - Settings**  
    Placeholder je zamijenjen punim ADMIN settings modulom koji upravlja velikim dijelom sistemske konfiguracije.

15. **Phase 15 - Barcodes & Export**  
    Zatvoren je barcode PDF flow za article i batch etikete, hardening deploy/migration puta i SPA serving za nested rute.

## 6. Važne stvari koje su dobro odrađene kroz proces

- **Kontrakti nisu ostavljeni implicitnima.** Više puta su zaključani točni API modovi da kasnije faze ne pregaze ranije workflowe.
- **Review je stvarno bio aktivan.** Phase 5, 6, 10, 11, 12, 13, 14 i 15 imaju jasan trag post-implementation remediacija.
- **Kompatibilnost među modulima je čuvana.** Najbolji primjer je `articles` i `orders` namespace koji su prošireni bez lomljenja Receiving/Draft Entry flowa.
- **Handoff protokol se isplatio.** Kad bi faza ostala bez orkestracijskog traga ili s pogrešnim testnim claimom, to je naknadno ispravljeno i dokumentirano.

## 7. Trenutno stanje V1

Stanje na **2026-03-17**:

- backend test suite: `255 passed in 16.63s`
- frontend lint: prolazi
- frontend production build: prolazi
- fresh Alembic upgrade na praznoj SQLite bazi: prolazi
- fresh `seed.py` na praznoj SQLite bazi: prolazi

Na razini repozitorija V1 je zatvoren kao funkcionalno kompletna baza za ručno i operativno testiranje.

### 7.1 Post-V1 stabilizacijski popravci zabilježeni 2026-03-17

Nakon bug reviewa zatvorena su dva stvarna backend rizika:

- logout revocation više nije process-local; refresh token JTI se sada persistira u `revoked_token` tablicu pa restart Flask procesa ili systemd restart ne “oživljava” odjavljene sesije
- dnevni operator draft sada koristi eksplicitni `DraftGroup.group_type = DAILY_OUTBOUND`, a baza enforcea najviše jednu `PENDING` daily outbound grupu po `operational_date`
- novi draftovi se više ne lijepe na već `APPROVED` ili `REJECTED` istodnevnu grupu; takva grupa ostaje u approval/history tragu, a operator dobiva novu `PENDING` daily outbound grupu
- inventory shortage draftovi ostaju odvojeni kroz `DraftGroup.group_type = INVENTORY_SHORTAGE`, pa isti operativni dan i dalje može imati i operator daily draft i zaseban inventory shortage approval bucket

## 8. Svjesne granice i otvoreni V1 rubovi

Ono što je namjerno ostavljeno jednostavnijim ili odgođeno:

- sustav je i dalje **single-location**
- nema live ERP/SAP integracije; export postoji, ali **SAP-specifični format nije do kraja definiran**
- barcode “print” je **PDF download/open/print**, ne direktni OS printer workflow
- hardware input je arhitekturno predviđen, ali nema pune integracije s vagom/skenerom
- `density` i `reorder_coverage_days` postoje u backendu, ali nisu aktivni dio Warehouse UI logike
- login screen i svježe non-ADMIN sesije još nemaju puni settings-backed branding/hydration
- deploy skripta je ojačana, ali full Pi/systemd smoke test nije dio ovog repo closeouta

## 9. Preporučena 2 vala velikih izmjena nakon intenzivnog testiranja

### Val 1 - Stabilizacija operativnih workflowa

Ovo bi trebao biti prvi veliki val odmah nakon stvarnog skladišnog testiranja.

Fokus:

- ispravci UX trenja u Draft Entry, Approvals, Receiving, Inventory Count i Employees workflowima
- dodatno zatvaranje edge caseova oko batcheva, stock raspoloživosti, approval bulk akcija, retry/fatal error flowa i paginacije
- optimizacija pretraga i listi na većim datasetovima
- čišćenje copy-ja, validacija i error poruka koje će se pokazati nejasnima u realnom radu
- širenje test matrice na “real world” scenarije koji se pojave tek u ručnom radu po smjenama

Očekivani rezultat:

- V1.1 koji ne dodaje veliki novi scope, nego učvršćuje postojeće module i uklanja operativne slabosti otkrivene na terenu.

### Val 2 - Produkcijsko očvršćivanje i dubinske funkcionalne nadogradnje

Nakon stabilizacije workflowa, drugi val bi trebao ići na stvari koje V1 svjesno odgađa.

Fokus:

- pravi Raspberry Pi deployment smoke test, backup/restore, recovery i operativni monitoring
- settings hydration za login i non-ADMIN experience
- definiranje i implementacija stvarnog SAP export kontrakta
- napredniji barcode/print flow i eventualna printer integracija
- aktivacija ili uklanjanje “future fields” kao što su `density` i `reorder_coverage_days`
- dublja automatizacija reorder logike i čišći most prema budućim hardware i MES proširenjima

Očekivani rezultat:

- V1.2 ili V2-prep sloj koji projekt prebacuje iz “dovršenog proizvoda u kodu” u “operativno kalibriran proizvod spreman za širu instalaciju”.

## 10. Zaključak

STOQIO V1 je uspješno dovršen kao dokumentiran, testiran i modularan WMS temelj. Najveća vrijednost ovog procesa nije samo u tome što je isporučeno 15 faza, nego što je iza svake faze ostao trag: što je napravljeno, što je promijenjeno nakon reviewa i koja su pravila od tada zaključana kao baseline.

Repo je danas u stanju koje ima smisla tretirati kao **V1-ready baseline za intenzivno ručno testiranje i operativno brušenje**, a ne kao prototip bez discipline. Upravo zato sljedeći korak ne bi trebao biti nekontrolirani novi scope, nego dva jasna vala: prvo stabilizacija stvarnog rada, pa zatim produkcijsko očvršćivanje i dublje nadogradnje.

## 11. Dokumenti koji su bili baza za ovaj recap

- root `README.md`
- ključni dokumenti u `stoqio_docs/`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- svi phase handoff folderi od `phase-01-project-setup` do `phase-15-barcodes-export`
- `handoff/phase-16-v1-stabilization`
- aktualni backend i frontend source kod
