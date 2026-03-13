# WMS — Domain Knowledge & Business Rules

**Status**: LOCKED — ne mijenjati bez eksplicitnog odobrenja vlasnika projekta  
**Izvor**: Iskustvo iz produkcijske implementacije v1 + razgovor s vlasnikom  

---

## 1. Osnovna načela inventara

### 1.1 Surplus-first konzumacija
Pri odobravanju izlaza:
1. Konzumiraj surplus prvo
2. Konzumiraj stock drugo
3. Odbij ako stock nije dovoljan

### 1.2 Stock nikad ne ide ispod nule
- Svaki approval i adjustment workflow mora validirati prije upisa
- Row-level locking obavezan za konkurentne operacije

### 1.3 Audit trail je obavezan
Svaka inventarna operacija mora kreirati transakcijski zapis s minimalnim poljima:
- `tx_type` — vrsta transakcije
- `occurred_at` — UTC timestamp
- `quantity` + `uom` — algebarski iznos promjene (negativno = izlaz)
- `user_id` — tko je napravio
- `meta` — kontekstni JSON

### 1.4 Sign konvencija transakcija
- **Negativno**: konzumacija (`OUTBOUND`, `STOCK_CONSUMED`, `SURPLUS_CONSUMED`)
- **Pozitivno**: dodavanje (`STOCK_RECEIPT`, pozitivni `INVENTORY_ADJUSTMENT`)

---

## 2. Artikli (Master Data)

### 2.1 Polja artikla
| Polje | Opis |
|-------|------|
| `article_no` | Jedinstveni broj artikla (tekst) |
| `description` | Naziv / opis |
| `category` | Normalizirana kategorija (enum) |
| `base_uom` | Osnovna mjerna jedinica |
| `pack_size` + `pack_uom` | Veličina pakiranja |
| `barcode` | Barkod artikla (generiran ili uvezen) |
| `manufacturer` | Proizvođač |
| `manufacturer_art_number` | Šifra artikla kod proizvođača |
| `reorder_threshold` | Prag za reorder (žuta zona) |
| `has_batch` | Da li se prati po šaržama |
| `is_active` | Aktivan/deaktiviran |
| `density` | Gustoća (za KG↔L konverziju) |

> **Napomena o supplier kodu**: Dobavljačev kod artikla (`supplier_article_code`) čuva se po dobavljaču u `ArticleSupplier` entitetu — ne na samom artiklu. Razlog: jedan artikl može imati više dobavljača, svaki s vlastitim kodom.

### 2.2 Kategorije artikala
```
equipment_installations       — oprema i instalacije
safety_equipment              — zaštitna oprema
operational_supplies          — operativni potrošni materijal
spare_parts_small_parts       — rezervni dijelovi
auxiliary_operating_materials — pomoćna sredstva
assembly_material             — montažni materijal
raw_material                  — sirovine
packaging_material            — ambalažni materijal
goods_merchandise             — roba za prodaju
maintenance_material          — materijal za održavanje
tools_small_equipment         — alati i sitna oprema
accessories_small_machines    — pribor za strojeve
```

### 2.3 Aliases (identifikatori)
- Svaki artikl može imati više aliases (alternativni nazivi, šifre)
- Koriste se za pretraživanje u Identifikator modulu
- Dedupliciraju se po normaliziranom inputu

### 2.4 Barkodovi
- Svaki artikl ima polje `barcode`
- Sustav mora podržavati **generiranje barkoda** unutar aplikacije
- Sustav mora podržavati **print barkoda** (PDF ili direktno na printer)
- Format barkoda: EAN-13 ili Code128 (konfigurabilno)
- Barkod je alternativni input za pretraživanje/unos — ručni unos uvijek ostaje

---

## 3. Šarže (Batches)

### 3.1 Pravila šarži
- Praćenje šarži kontrolira se na razini artikla (`has_batch` flag)
- `is_paint` je samo klasifikacijska oznaka — **ne utječe** na logiku šarži
- Ako artikl ima `has_batch = true`, batch + expiry datum su obavezni

### 3.2 Batch code validacija
Regex: `^\d{4,5}$|^\d{9,12}$`

### 3.3 Batch expiry mismatch
Ako postojeći batch ima drugačiji expiry datum od onog na primki → vrati `BATCH_EXPIRY_MISMATCH` (409)

---

## 4. Stock i Surplus

### 4.1 Razlika Stock / Surplus
- **Stock** = redovne zalihe, povećava se samo kroz receiving workflow
- **Surplus** = višak otkriven inventurom, konzumira se prvi

### 4.2 Inventura — handling discrepancija
- `counted > system_total` → razlika ide u surplus automatski
- `counted = system_total` → nema promjene
- `counted < system_total` → kreira shortage draft za admin odobrenje

---

## 5. Draft → Approval workflow

### 5.1 Lifecycle
```
DRAFT → APPROVED
      → REJECTED
```

### 5.2 Pravila
- Ništa ne mijenja stock dok admin ne odobri
- Pre-approval editi prepisuju draft vrijednosti (nema correction transakcija prije odobrenja)
- Dnevna agregacija moguća samo za isti `article + batch`
- Isti artikl u različitim šaržama = zasebni redovi

### 5.3 Draft tipovi
- `OUTBOUND` — izlaz materijala (operator unosi)
- `INVENTORY_SHORTAGE` — manjak otkriven inventurom

### 5.4 Hardware identity polja (za buduću integraciju)
Svaki draft pamti izvor:
```
scale_id, scanner_id, station_id, source_label, source_meta (JSON)
```

### 5.5 Idempotency
- Create endpointi primaju `client_event_id`
- Duplikati se tretiraju idempotentno

---

## 6. Primanje robe (Receiving / Ulaz)

### 6.1 Pravila
- Receiving povećava **samo stock** (ne surplus)
- ADMIN-only operacija
- `delivery_note_number` je obavezan za traceability
- Može biti linked na order line (`order_line_id`) ili ad-hoc (s napomenom)

### 6.2 Ad-hoc receiving
- Dozvoljeno bez narudžbenice
- Obavezna explanatory napomena
- Ako ad-hoc primka nema `unit_price`:
  - postojeći stock red zadržava postojeći `average_price`
  - novi stock red se inicijalizira s `average_price = 0.0000`

---

## 7. Narudžbenice (Orders)

### 7.1 Lifecycle
```
OPEN → CLOSED (automatski kad su sve aktivne linije ispunjene)
```

### 7.2 Order number format
Auto-generirani: `ORD-0001`, `ORD-0002`, ...
Može biti i manual (mora biti jedinstven)
Auto-generirani `ORD-####` niz koristi persistentni counter po instalaciji.
Ako admin ručno spremi broj koji također odgovara `ORD-####` formatu, sljedeći auto-generirani broj nastavlja iznad tog suffixa.

### 7.3 Order line statusi
`OPEN | CLOSED | REMOVED`

### 7.4 Pravila
- Admin može editirati/brisati neispunjene linije
- Status narudžbe recalculate se odmah nakon svake promjene

---

## 8. Zaposlenici i osobna izdavanja

### 8.1 Zaposlenici (v1)
- Nisu korisnici sustava — samo evidencija
- Imaju ID zaposlenika (upis pri izdavanju)
- Pohranjuju se u bazi kao master data

### 8.2 Osobna izdavanja
- Određeni artikli (zaštitna oprema, alati, radna odjeća) izdaju se **osobno zaposleniku**
- Pri izdavanju se upisuje ID zaposlenika
- Evidencija: tko je što i kada primio

### 8.3 Godišnje kvote
- Po kategoriji artikla definira se godišnja kvota po zaposleniku
- Primjer: "zaštitne hlače — max 2 kom/god"
- Sustav upozorava (ili blokira) pri prekoračenju kvote
- Kvote su konfigurabine po kategoriji / artiklu / zaposleniku

### 8.4 Dosije zaposlenika
- Pregled svega što je zaposlenik primio kroz povijest
- Pregled iskorištenosti godišnjih kvota
- Dostupno roli ADMINISTRACIJA i ADMIN

### 8.5 Buduće proširenje (MES)
- Zaposlenici dobivaju performans metrike iz MES modula
- V1 ne implementira ovo

---

## 9. Multi-unit semantika

### 9.1 Podržane jedinice
Otvoreni katalog — nove jedinice se dodaju pri unosu i ostaju u katalogu.
Primjeri: `kg`, `l`, `kom`, `pak`, `m`, `m²`, `pár` ...

### 9.2 Konverzije
- Backend podržava konverzije između `KG` i `L` (density-based)
- Nepoznate konverzije vraćaju `UNSUPPORTED_UOM_CONVERSION` (400)

### 9.3 Baza
- Sve količine se pohranjuju kao `quantity` (Numeric 14,3) + `uom` (String)
- Nema `quantity_kg` — to je legacy iz v1 koji se ne ponavlja

---

## 10. Lokacije

### 10.1 V1 policy
- Jedna lokacija po instalaciji (konfigurabilno pri setup-u)
- UI ne prikazuje location selector u v1
- API prihvaća `location_id` za forward compatibility

### 10.2 Buduće
- Multi-lokacijski support planiran, ali nije u v1 scope

---

## 11. Reorder threshold

- `reorder_threshold` definiran po artiklu
- **Žuta zona**: `threshold < qty <= threshold * 1.10`
- **Crvena zona**: `qty <= threshold`
- Vidljivo u izvještajima i pregledu skladišta

---

## 12. Timezone semantika

- Timestampovi se pohranjuju u **UTC**
- Dnevno grupiranje za approvals: po operativnoj zoni (`Europe/Berlin` default, konfigurabilno)
- Buduće: timezone konfigurabilna per-lokacija

---

## 13. Sigurnost

- JWT auth, fail-safe: aplikacija se ne pokreće u produkciji s default/slabim JWT secretom
- Rate limiting na auth endpointima
- Lozinke: `pbkdf2:sha256`
- **First-run setup**: POST `/api/v1/setup` zahtijeva važeći admin JWT token — nije javni endpoint. Admin se prijavi s defaultnim credentialima, a ako nema Location zapisa, automatski se preusmjerava na `/setup`. Tek nakon kreiranja lokacije aplikacija postaje u potpunosti operativna.

---

## 14. Identifikator modul

- Pretraživanje artikla po: broju artikla, opisu, aliasu, barkodu
- Dostupno za više rola (OPERATOR, KONTROLA, ADMINISTRACIJA, ADMIN)
- Ako artikl ne postoji → korisnik može poslati "missing article" report
- Admin ima queue za obradu reportova
- Isti reportovi se dedupliciraju/spajaju po normaliziranom inputu
- Report se zatvara samo eksplicitnom admin akcijom

---

## 15. Settings persistence

Konfiguracijske postavke instalacije perzistiraju se na dva načina:

- **`SystemConfig`** (key-value tablica): general language, barcode format, barcode printer, export format
- **`RoleDisplayName`** (5 fiksnih redova): prikaz naziva rola u UI-u
- **`Location`**: name i timezone (dio "general" postavki)
- **`Category`** i **`UomCatalog`**: labeli i flagovi koji se uređuju u Settingsima su direktno na tim entitetima

Sve ostale postavke (korisnici, kategorije, UOM, kvote) ažuriraju se direktno na svojim entitetima putem Settings API-a.

---

## 16. Supplier master data

- **Kreiranje i uređivanje dobavljača** odvija se isključivo u **Settings → Dobavljači** sekciji
- Supplier je master data — kao kategorije i UOM, upravlja se centralno, ne po modulu
- Warehouse / Article detail prikazuje dobavljače linked na artikl (read-only pogled)
- Linking dobavljača na artikl (`ArticleSupplier`) radi se iz Article detail forme
- `supplier_article_code` živi na `ArticleSupplier` (po dobavljaču), ne na `Article` — jedan artikl može imati različite kodove kod različitih dobavljača
