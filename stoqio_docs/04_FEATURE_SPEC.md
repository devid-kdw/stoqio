# WMS — Feature Specification v1

**Status**: Aktivan dokument  
**Scope**: v1 — WMS jezgra (MES modul nije u scope)

---

## Pregled modula

| Modul | Sistemski naziv | Dostupno rolama |
|-------|----------------|-----------------|
| Unos izlaza | Draft Entry | ADMIN, OPERATOR |
| Odobravanje | Approvals | ADMIN |
| Ulaz robe | Receiving | ADMIN |
| Narudžbenice | Orders | ADMIN (MANAGER read-only) |
| Skladište | Warehouse | ADMIN (MANAGER read-only) |
| Identifikator | Identifier | ADMIN, MANAGER, WAREHOUSE_STAFF, VIEWER |
| Zaposlenici | Employees | ADMIN (WAREHOUSE_STAFF pregled) |
| Inventura | Inventory Count | ADMIN |
| Izvještaji | Reports | ADMIN, MANAGER |
| Konfiguracija | Settings | ADMIN |

---

## 1. Unos izlaza (Draft Entry)

**Namjena**: Operater evidentira izlaz materijala koji čeka admin odobrenje.

**Pravila**:
- Ništa ne mijenja stock dok admin ne odobri
- Source može biti: `scale` (vaga, default) ili `manual` (ručni unos)
- Wire/API vrijednosti za source ostaju lowercase: `scale` i `manual`.
- Vaga je default na prvom učitavanju ekrana
- `client_event_id` se generira interno (hidden) — osigurava idempotency

**Polja unosa**:
- Artikl (broj artikla ili barkod skeniranje)
- Količina + UOM
- Batch (prikazuje se samo ako artikl ima `has_batch = true`)
- Šifra zaposlenika (opcionalno)
- Napomena za dnevni draft (opcionalno, vrijedi za cijeli današnji draft)

**Hardware identity** (snima se uz draft, za buduću integraciju):
- `scale_id`, `scanner_id`, `station_id`, `source_label`, `source_meta`

**OPERATOR prozor**: Samo ovaj ekran — ništa više nije vidljivo.

---

## 2. Odobravanje (Approvals)

**Namjena**: Admin pregleda i odobrava ili odbija pending draftove.

**Pravila**:
- Draftovi grupirani po operativnom danu (konfigurabilna timezone, default Europe/Berlin)
- Dnevna agregacija: isti `article + batch` = jedan red
- Isti artikl u različitim batchevima = zasebni redovi
- Bulk approve/reject po grupi
- Pre-approval edit prepisuje draft vrijednosti (ne kreira correction transakciju)
- Approval kreira transakciju i mijenja stock (surplus-first logika)

---

## 3. Ulaz robe (Receiving)

**Namjena**: Admin prima robu i povećava stock.

**Pravila**:
- Samo ADMIN
- Receiving povećava **samo stock** (ne surplus)
- `delivery_note_number` je obavezan
- Može biti linked na order line (`order_line_id`) ili ad-hoc
- Ad-hoc receiving zahtijeva explanatory napomenu
- History primki prikazan unutar istog ekrana (ne zasebna stranica)

---

## 4. Narudžbenice (Orders)

**Namjena**: Praćenje nabavnih narudžbi i njihovog ispunjenja.

**Lifecycle**: `OPEN → CLOSED` (automatski kad sve aktivne linije ispunjene)

**Order broj**: Auto-generiran `ORD-0001`, `ORD-0002`... ili manual (mora biti jedinstven)

**Order polja**: dobavljač, napomena, status, linije

**Order line polja**: artikl, naručena količina, primljena količina, UOM, delivery_date, status, napomena

**Line statusi**: `OPEN | CLOSED | REMOVED`

**Pravila**:
- Admin može editirati/brisati neispunjene linije
- Status narudžbe recalculate se odmah nakon svake promjene linije
- Receiving može biti linked na order line ili ad-hoc
- `GET /api/v1/orders?q=...` ostaje exact-match compatibility mode za Receiving, a Orders UI koristi paginirani list mode.

---

## 5. Skladište / Pregled artikala (Warehouse)

**Namjena**: Pregled stanja zaliha i upravljanje master podacima artikala.

**Pregled zaliha**:
- Stanje po artiklu: stock + surplus
- Reorder threshold vizualizacija:
  - 🔴 Crvena zona: `qty <= threshold`
  - 🟡 Žuta zona: `threshold < qty <= threshold * 1.10`
- Batch pregled po artiklu (expiry datumi)

**Upravljanje artiklima** (ADMIN only):
- Create, edit, deactivate artikl
- Polja: article_no, description, category, base_uom, pack_size, manufacturer, manufacturer_art_number, reorder_threshold, has_batch, density, is_active
- Supplier kodovi žive na `ArticleSupplier.supplier_article_code` (po dobavljaču) — ne na artiklu direktno
- Aliases management (alternativni nazivi za Identifikator)

**Barkodovi** (ADMIN only):
- Generiranje barkoda po artiklu (EAN-13 ili Code128)
- **PDF preuzimanje**: `GET /api/v1/articles/{id}/barcode` / `GET /api/v1/batches/{id}/barcode` — PDF naljepnica preuzima se u pregledniku
- **Direktni ispis**: `POST /api/v1/articles/{id}/barcode/print` / `POST /api/v1/batches/{id}/barcode/print` — ZPL naljepnica šalje se izravno na mrežni label printer; zahtijeva `label_printer_ip` u Settings
- **Budući raw-label mod**: nije implementiran
- Barkod field na artiklu — može biti uvezen ili generiran

---

## 6. Identifikator

**Namjena**: Brzo pretraživanje artikla po bilo kojoj poznatoj oznaci.

**Pretraživanje po**: broju artikla, opisu, aliasu, barkodu

**Rezultat**: puni detalji artikla (opis, kategorija, UOM, stanje zaliha ako rola ima pristup)

**Missing article report**:
- Ako artikl ne postoji → korisnik šalje report
- Isti reportovi se dedupliciraju po normaliziranom inputu
- Admin queue za obradu reportova
- Report se zatvara samo eksplicitnom admin akcijom (status: `OPEN → RESOLVED`)

---

## 7. Zaposlenici (Employees)

**Namjena**: Evidencija osobnih izdavanja i praćenje godišnjih kvota.

**Važno**: Zaposlenici su samo evidencija u v1 — **nemaju vlastiti login**.

### 7.1 Master data zaposlenika
- ID zaposlenika (interni ili HR broj)
- Ime i prezime
- Odjel / radno mjesto
- Status (aktivan/neaktivan)

### 7.2 Osobna izdavanja
- Određeni artikli (zaštitna oprema, alati, radna odjeća) izdaju se osobno
- Kategorija artikla određuje je li osobno izdavanje
- Pri izdavanju: artikl + zaposlenik + količina + datum + napomena
- ADMIN only

### 7.3 Godišnje kvote
- Po kategoriji artikla definira se godišnja kvota po zaposleniku
- Primjer: "zaštitne hlače — max 2 kom/god"
- Kvote su konfigurabine: može se postaviti default po kategoriji, override po artiklu ili po zaposleniku
- Sustav upozorava pri prekoračenju kvote (soft warning ili hard block — konfigurabilno)
- Kvote se resetiraju godišnje (datum reseta konfigurabilno)

### 7.4 Dosije zaposlenika
- Pregled svega što je zaposlenik primio kroz povijest
- Pregled iskorištenosti godišnjih kvota (tekuća godina)
- Dostupno: ADMIN (uređivanje), WAREHOUSE_STAFF (pregled)

### 7.5 Buduće proširenje (MES — nije v1)
- Performans metrike iz MES modula
- Praćenje komada po zaposleniku

---

## 8. Inventura (Inventory Count)

**Namjena**: Periodično prebrojavanje i usklađivanje stanja.

**Proces**:
1. Admin pokreće inventuru
2. Prikaz svih artikala s trenutnim sistemskim stanjem
3. Unos prebrojanog stanja po artiklu (i batchu ako has_batch)
4. Automatska obrada discrepancija:
   - `counted > system` → razlika ide u surplus automatski
   - `counted = system` → nema promjene
   - `counted < system` → kreira shortage draft za admin odobrenje

---

## 9. Izvještaji (Reports)

**Namjena**: Pregled i export podataka za upravljanje i SAP/ERP.

### 9.1 Inventurna lista
- Prikaz: artikl + batch, trenutno stanje, UOM
- Export: Excel (SAP-kompatibilan format)

### 9.2 Surplus lista
- Prikaz: artikl + batch, surplus količina, datum nastanka

### 9.3 Statistike
- Top potrošači po artiklu (period: tjedan/mjesec/godina)
- Kretanje robe kroz vrijeme (ulaz/izlaz grafikon)
- Pregled reorder zona (crvena/žuta)
- Osobna izdavanja po zaposleniku
- Iskorištenost godišnjih kvota
- Ne splitati liste po UOM — sve u jednom prikazu

### 9.4 Identifikator queue
- Admin pregled svih missing article reportova
- Status filteri: OPEN / RESOLVED

### 9.5 Export
- Svi izvještaji exportabilni u Excel
- Format konfigurabilan za SAP uvoz

---

## 10. Konfiguracija (Settings)

**Namjena**: Postavljanje sustava pri instalaciji i tekuće konfiguriranje.

**Postavke**:
- Naziv firme / lokacije
- Default jezik UI-a (`hr`, `en`, `de`, `hu`)
- Operativna timezone (default: `Europe/Berlin`)
- Display nazivi rola (OPERATOR → "Operater lakirnice" itd.)
- UOM katalog (pregled i dodavanje)
- Kategorije artikala
- Reorder threshold defaulti
- Kvote za osobna izdavanja (default po kategoriji)
- Datum godišnjeg reseta kvota
- Barkod format (EAN-13 / Code128)
- Direktni label printer: `label_printer_ip`, `label_printer_port`, `label_printer_model`
- `barcode_printer` (OS-level printer name, hint za PDF workflow)
- Export format za SAP

---

## Zajednički UI zahtjevi

- **Responzivno**: primarno tablet + desktop, ne mobile
- **Sidebar navigation**: vidljiv samo moduli dostupni roli korisnika
- **i18n**: HR default, EN/DE/HU scaffold u v1, puna podrška later
- **Ručni unos uvijek dostupan**: hardware (vaga, skener) je bonus input, ne preduvjet
- **Barkod input**: obični text field koji prima skener kao keyboard (plug & play)
- **Widths**: responzivni široki content area, ne uski centered containers
- **Error handling**: jasne error poruke na jeziku UI-a
- **Loading states**: svaki async poziv ima loading indikator
- **Empty states**: svaka lista ima human-readable empty state

---

## Što nije u v1 scope

- MES modul (praćenje komada u proizvodnji)
- Multi-lokacijski support
- Live ERP/SAP integracija (samo Excel export)
- Zaposlenici s vlastitim loginom
- OPERATOR_SKLADISTE rola (2. smjena)
- Mobile app
- Hardware integracija (vaga, skener) — arhitektura je sprema, ali nije implementirano
