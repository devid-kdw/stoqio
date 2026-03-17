# WMS — Data Model Overview

**Status**: Aktivan dokument
**Verzija**: v1

---

## Napomena o batch_id

`batch_id` je **nullable** na svim entitetima gdje se pojavljuje. Artikli koji nemaju `has_batch = true` nemaju šaržu, ali i dalje mogu imati stock, surplus, draftove, transakcije itd. NULL `batch_id` znači "artikl bez šarže".

---

## Pregled entiteta

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Supplier   │────<│   Article   │────<│    Batch    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                           │                   │ (nullable)
                    ┌──────┴──────┐      ┌──────┴──────┐
                    │    Stock    │      │   Surplus   │
                    └─────────────┘      └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴───┐  ┌─────┴─────┐  ┌──┴───────────┐
       │  Draft   │  │ Receiving │  │InventoryCount│
       └──────────┘  └───────────┘  └──────────────┘
              │            │
       ┌──────┴───┐  ┌─────┴─────┐
       │ Approval │  │   Order   │
       └──────────┘  └───────────┘

┌─────────────┐     ┌─────────────────┐
│  Employee   │────<│ PersonalIssuance│
└─────────────┘     └─────────────────┘

┌─────────────┐
│    User     │
└─────────────┘

┌─────────────┐
│ Transaction │  ← audit trail za sve inventory operacije
└─────────────┘

┌──────────────┐     ┌──────────────────┐
│ SystemConfig │     │ RoleDisplayName  │
└──────────────┘     └──────────────────┘
← settings persistence (general, barcode, export, role labels)
```

---

## Entiteti

### 1. Supplier (Dobavljač)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `internal_code` | string UNIQUE | Interni kod dobavljača |
| `name` | string | Naziv dobavljača |
| `contact_person` | string nullable | Kontakt osoba |
| `phone` | string nullable | Telefon |
| `email` | string nullable | Email |
| `address` | string nullable | Adresa |
| `iban` | string nullable | IBAN (opcionalno) |
| `note` | text nullable | Napomena |
| `is_active` | bool | Aktivan/deaktiviran |
| `created_at` | timestamp UTC | |

---

### 2. Article (Artikl)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `article_no` | string UNIQUE | Interni kod artikla |
| `description` | string | Naziv artikla |
| `category_id` | FK → Category | Kategorija |
| `base_uom` | FK → UomCatalog | Osnovna mjerna jedinica (kg, kom, l...) |
| `pack_size` | decimal nullable | Veličina pakiranja (npr. 25) |
| `pack_uom` | FK → UomCatalog nullable | Jedinica pakiranja (npr. kanta) |
| `barcode` | string nullable | Barkod artikla (generiran ili uvezen) |
| `manufacturer` | string nullable | Naziv proizvođača |
| `manufacturer_art_number` | string nullable | Šifra artikla kod proizvođača |
| `has_batch` | bool | Prati li se po šaržama |
| `reorder_threshold` | decimal nullable | Trenutni prag za naručivanje |
| `reorder_coverage_days` | int nullable | Ciljna pokrivenost u danima (za auto-izračun thresholda) |
| `density` | decimal | Gustoća za KG↔L konverziju (default 1.0) |
| `is_active` | bool | Aktivan/deaktiviran |
| `created_at` | timestamp UTC | |
| `updated_at` | timestamp UTC nullable | |

> **Napomena o pakiranju**: Stanje se uvijek vodi u `base_uom`. `pack_size` je informativno polje — sustav prikazuje "100 kg (4 kante po 25 kg)" ali interno pamti samo 100 kg.

> **Napomena o reorder thresholdu**: Pri prvom unosu artikla, threshold se unosi ručno. Nakon dovoljno transakcija, sustav može predložiti novi threshold baziran na prosječnoj potrošnji × `reorder_coverage_days`. Korisnik uvijek može override.

---

### 3. ArticleSupplier (Artikl ↔ Dobavljač)

Jedan artikl može imati više dobavljača. Svaki zapis pamti dobavljačev kod i zadnju cijenu.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `article_id` | FK → Article | |
| `supplier_id` | FK → Supplier | |
| `supplier_article_code` | string nullable | Dobavljačev kod za ovaj artikl |
| `last_price` | decimal nullable | Zadnja nabavna cijena |
| `last_ordered_at` | timestamp nullable | Datum zadnje narudžbe |
| `is_preferred` | bool | Preferiran dobavljač za ovaj artikl |

---

### 4. ArticleAlias

Alternativni nazivi i šifre za pretraživanje u Identifikatoru.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `article_id` | FK → Article | |
| `alias` | string | Alternativni naziv/šifra |
| `normalized` | string | Normaliziran alias za pretragu |

---

### 5. Category (Kategorija artikla)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `key` | string UNIQUE | Sistemski ključ (EN, npr. `safety_equipment`) |
| `label_hr` | string | Hrvatski naziv |
| `label_en` | string nullable | Engleski naziv |
| `label_de` | string nullable | Njemački naziv (scaffold — nije popunjen u v1 seedu) |
| `label_hu` | string nullable | Mađarski naziv (scaffold — nije popunjen u v1 seedu) |
| `is_personal_issue` | bool | Izdaje li se osobno zaposlenicima |
| `default_annual_quota` | decimal nullable | Default godišnja kvota po zaposleniku |
| `quota_uom` | string nullable | Jedinica kvote |
| `is_active` | bool | |

> **Lokalizacija master data u v1**: `label_hr` je uvijek popunjen. `label_en` se puni u seedu. `label_de` i `label_hu` su nullable scaffoldi — UI chrome (navigacija, labeli) lokaliziran je putem i18n fajlova, ali master data (kategorije, UOM) nisu prevedeni na DE/HU u v1.

---

### 6. UomCatalog (Katalog mjernih jedinica)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `code` | string UNIQUE | Kod jedinice (npr. `kg`, `kom`, `pak`) |
| `label_hr` | string | Hrvatski naziv |
| `label_en` | string nullable | Engleski naziv |
| `decimal_display` | bool | `true` = prikaz s 2 decimale (kg, l, m...); `false` = prikaz kao cijeli broj (kom, pak, pár) |

> Otvoreni katalog — admin može dodavati nove jedinice. Kod dodavanja nove jedinice, admin mora odrediti `decimal_display` flag. DE/HU labele nisu u scope v1 — vidi napomenu kod Category.

---

### 7. Batch (Šarža)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `article_id` | FK → Article | |
| `batch_code` | string | Kod šarže |
| `expiry_date` | date | Datum isteka |
| `barcode` | string nullable | Barkod šarže (generiran pri zaprimanju) |
| `created_at` | timestamp UTC | |

> **Pravilo**: Batch postoji samo za artikle s `has_batch = true`.
> **FEFO logika**: Izlaz uvijek konzumira šaržu s najbližim expiry datumom.
> **Barkod šarže**: Generira se pri zaprimanju. Broj tiskanih barkodova = broj primljenih pakiranja.
> **Validacija batch koda**: `^\d{4,5}$|^\d{9,12}$`
> **Batch expiry mismatch**: Ako pri prijemu batch već postoji s drugačijim expiry datumom → 409 error.

---

### 8. Stock (Zaliha)

Trenutno stanje zaliha po artiklu i šarži.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `location_id` | FK → Location | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `quantity` | decimal(14,3) | Trenutna količina (≥ 0) |
| `uom` | string | Mjerna jedinica |
| `average_price` | decimal(14,4) | Prosječna nabavna cijena (weighted average) |
| `last_updated` | timestamp UTC | |

> **Constraint**: `quantity >= 0` — stock nikad ne ide ispod nule.
> **Unique**: `(location_id, article_id, batch_id)` — PostgreSQL tretira NULL kao "nema šarže".
> **Receiving fallback**: ako ad-hoc primka dođe bez `unit_price` i stock red već postoji, `average_price` ostaje nepromijenjen; ako stock red ne postoji, inicijalizira se na `0.0000`.

---

### 9. Surplus (Višak)

Viškovi otkriveni inventurom. Konzumiraju se prije stocka.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `location_id` | FK → Location | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `quantity` | decimal(14,3) | Količina viška |
| `uom` | string | |
| `created_at` | timestamp UTC | Kad je višak otkriven |

---

### 10. Draft (Nacrt izlaza)

Staging tablica — izlaz čeka admin odobrenje.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `draft_group_id` | FK → DraftGroup | Approval grupa draftova (daily outbound ili inventory shortage batch) |
| `location_id` | FK → Location | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `quantity` | decimal(14,3) | Količina izlaza |
| `uom` | string | |
| `status` | enum | `DRAFT` / `APPROVED` / `REJECTED` |
| `draft_type` | enum | `OUTBOUND` / `INVENTORY_SHORTAGE` |
| `source` | enum | `scale` / `manual` |
| `scale_id` | string nullable | ID vage (za buduću HW integraciju) |
| `scanner_id` | string nullable | ID skenera |
| `station_id` | string nullable | ID radne stanice |
| `source_label` | string nullable | Human-readable oznaka izvora (npr. "Vaga 1 - lakirnica") |
| `source_meta` | JSON nullable | Dodatni HW metadata |
| `client_event_id` | string UNIQUE | Idempotency key |
| `employee_id_ref` | string nullable | ID zaposlenika koji preuzima materijal (slobodni tekst, bez FK validacije u v1) |
| `created_by` | FK → User | |
| `created_at` | timestamp UTC | |

---

### 11. DraftGroup (Grupa nacrta)

Dnevni izlaz — grupa draftova koji se zajedno odobravaju.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `group_number` | string UNIQUE | Auto-generirani broj izlaza (npr. `IZL-0001`) |
| `description` | text nullable | Napomena / opis za cijeli dnevni draft |
| `status` | enum | `PENDING` / `APPROVED` / `REJECTED` |
| `group_type` | enum | `DAILY_OUTBOUND` / `INVENTORY_SHORTAGE` |
| `operational_date` | date | Operativni dan (Europe/Berlin tz) |
| `created_by` | FK → User | |
| `created_at` | timestamp UTC | |

> `DAILY_OUTBOUND` je operatorov trenutačni dnevni izlaz. `INVENTORY_SHORTAGE` je grupa shortage draftova nastala iz jednog završetka inventure.
>
> V1 hardening after 2026-03-17: baza enforcea **najviše jednu `PENDING` `DAILY_OUTBOUND` grupu po `operational_date`**. Zatvorene (`APPROVED` / `REJECTED`) istodnevne grupe smiju koegzistirati s novom otvorenom dnevnom grupom, a inventory shortage grupe ostaju odvojene preko `group_type`.

---

### 12. ApprovalAction

Zapis admin odobrenja/odbijanja.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `draft_id` | FK → Draft | |
| `actor_id` | FK → User | Admin koji je odobrio/odbio |
| `action` | enum | `APPROVED` / `REJECTED` |
| `note` | text nullable | Razlog odbijanja (opcionalno) |
| `acted_at` | timestamp UTC | |

---

### 13. Order (Narudžbenica)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `order_number` | string UNIQUE | Auto: `ORD-0001` ili manual |
| `supplier_id` | FK → Supplier | |
| `supplier_confirmation_number` | string nullable | Broj potvrde narudžbe od dobavljača (unosi se naknadno) |
| `status` | enum | `OPEN` / `CLOSED` |
| `note` | text nullable | |
| `created_by` | FK → User | |
| `created_at` | timestamp UTC | |
| `updated_at` | timestamp UTC nullable | |

---

### 14. OrderLine (Linija narudžbenice)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `order_id` | FK → Order | |
| `article_id` | FK → Article | |
| `supplier_article_code` | string nullable | Dobavljačev kod u trenutku narudžbe |
| `ordered_qty` | decimal(14,3) | Naručena količina |
| `received_qty` | decimal(14,3) | Primljena količina (kumulativno, default 0) |
| `uom` | string | |
| `unit_price` | decimal(14,4) nullable | Dogovorena cijena |
| `delivery_date` | date nullable | Očekivani datum isporuke |
| `status` | enum | `OPEN` / `CLOSED` / `REMOVED` |
| `note` | text nullable | |

---

### 15. Receiving (Primka)

Zapis zaprimanja robe na skladište.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `order_line_id` | FK → OrderLine / **NULL** | NULL za ad-hoc primku |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `location_id` | FK → Location | |
| `quantity` | decimal(14,3) | Primljena količina |
| `uom` | string | |
| `unit_price` | decimal(14,4) nullable | Cijena na ovoj primki (za avg price izračun) |
| `delivery_note_number` | string | Broj otpremnice dobavljača (obavezan) |
| `note` | text nullable | Obavezno za ad-hoc primku |
| `barcodes_printed` | int | Broj tiskanih barkodova šarže (0 ako nema batch) |
| `received_by` | FK → User | |
| `received_at` | timestamp UTC | |

---

### 16. Transaction (Audit trail)

Nepromjenjiv zapis svake inventory operacije.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `tx_type` | enum | `STOCK_RECEIPT` / `OUTBOUND` / `SURPLUS_CONSUMED` / `STOCK_CONSUMED` / `INVENTORY_ADJUSTMENT` / `WRITEOFF` / `PERSONAL_ISSUE` |
| `occurred_at` | timestamp UTC | |
| `location_id` | FK → Location | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `quantity` | decimal(14,3) | Algebarski iznos (negativno = izlaz) |
| `uom` | string | |
| `unit_price` | decimal(14,4) nullable | Cijena u trenutku transakcije |
| `user_id` | FK → User | |
| `reference_type` | string nullable | `draft` / `receiving` / `inventory_count` / `issuance` / `writeoff` |
| `reference_id` | int nullable | ID referenciranog zapisa |
| `order_number` | string nullable | Broj narudžbe (ako postoji) |
| `delivery_note_number` | string nullable | Broj otpremnice (ako postoji) |
| `meta` | JSON nullable | Dodatni kontekst |

---

### 17. InventoryCount (Inventura)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `status` | enum | `IN_PROGRESS` / `COMPLETED` |
| `note` | text nullable | |
| `started_by` | FK → User | |
| `started_at` | timestamp UTC | |
| `completed_at` | timestamp UTC nullable | |

---

### 18. InventoryCountLine (Linija inventure)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `inventory_count_id` | FK → InventoryCount | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `system_quantity` | decimal(14,3) | Stanje u sustavu u trenutku inventure |
| `counted_quantity` | decimal(14,3) nullable | Prebrojano stanje (NULL = nije još prebrojan) |
| `uom` | string | |
| `difference` | decimal(14,3) nullable | `counted - system` (izračunato) |
| `resolution` | enum nullable | `SURPLUS_ADDED` / `SHORTAGE_DRAFT_CREATED` / `NO_CHANGE` |

---

### 19. Employee (Zaposlenik)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `employee_id` | string UNIQUE | Interni HR broj zaposlenika |
| `first_name` | string | |
| `last_name` | string | |
| `department` | string nullable | Odjel |
| `job_title` | string nullable | Radno mjesto |
| `is_active` | bool | |
| `created_at` | timestamp UTC | |

---

### 20. PersonalIssuance (Osobno izdavanje)

Izdavanje zaštitne opreme, alata, radne odjeće zaposleniku.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `employee_id` | FK → Employee | |
| `article_id` | FK → Article | |
| `batch_id` | FK → Batch / **NULL** | NULL ako artikl nema `has_batch` |
| `quantity` | decimal(14,3) | |
| `uom` | string | |
| `issued_by` | FK → User | Admin koji je izdao |
| `issued_at` | timestamp UTC | |
| `note` | text nullable | |

---

### 21. AnnualQuota (Godišnja kvota)

Definira koliko čega zaposlenik može primiti godišnje.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `job_title` | string nullable | Radno mjesto na koje se kvota odnosi (NULL = vrijedi za sve) |
| `category_id` | FK → Category / **NULL** | Default kvota po kategoriji (NULL ako je per-article) |
| `article_id` | FK → Article / **NULL** | Override po artiklu (NULL ako je per-category) |
| `employee_id` | FK → Employee / **NULL** | Override po zaposleniku (NULL = vrijedi za sve s tim job_title) |
| `quantity` | decimal(14,3) | Max godišnja količina |
| `uom` | string | |
| `reset_month` | int | Mjesec godišnjeg reseta (default: 1 = siječanj) |
| `enforcement` | enum | `WARN` / `BLOCK` |

> **Prioritet primjene** (od najvišeg prema najnižem):
> 1. Override po zaposleniku + artiklu (`employee_id` + `article_id` postavljeni)
> 2. Override po artiklu za sve (`article_id` postavljen, `employee_id` NULL)
> 3. Default po job_title + kategoriji (`job_title` + `category_id` postavljeni, `employee_id` NULL)
>
> Kvote iz Settingsa definiraju se po `job_title` i primjenjuju se na sve zaposlenike s tim `job_title`.
> Individualni override po zaposleniku postavlja se iz dosijea zaposlenika.

---

### 22. User (Korisnik sustava)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `username` | string UNIQUE | |
| `password_hash` | string | pbkdf2:sha256 |
| `role` | enum | `ADMIN` / `MANAGER` / `WAREHOUSE_STAFF` / `VIEWER` / `OPERATOR` |
| `employee_id` | FK → Employee / **NULL** | Opcionalno — ako je korisnik i zaposlenik |
| `is_active` | bool | |
| `created_at` | timestamp UTC | |

---

### 22a. RevokedToken (JWT revocation registry)

Persisted server-side evidencija odjavljenih JWT refresh tokena.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `jti` | string UNIQUE | JWT ID opozvanog tokena |
| `token_type` | string | Trenutno se koristi za `refresh` logout opozive |
| `user_id` | FK → User / **NULL** | Korisnik kojem je token pripadao |
| `revoked_at` | timestamp UTC | Kada je token opozvan |
| `expires_at` | timestamp UTC nullable | Originalni expiry tokena, za kasniji cleanup |

> V1 hardening after 2026-03-17: logout revocation više nije process-local. Restart procesa ne smije ponovno učiniti odjavljeni refresh token važećim.

---

### 23. Location (Lokacija)

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `name` | string | Naziv lokacije |
| `timezone` | string | Operativna timezone (default: `Europe/Berlin`) |
| `is_active` | bool | |

> V1: jedna lokacija po instalaciji. API uvijek prima `location_id` za forward compatibility s multi-lokacijskim sustavom.

---

### 24. MissingArticleReport

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `reported_by` | FK → User | |
| `search_term` | string | Što je korisnik tražio |
| `normalized_term` | string | Normaliziran term za dedupliciranje |
| `report_count` | int | Broj puta koliko je isti otvoreni report prijavljen |
| `status` | enum | `OPEN` / `RESOLVED` |
| `resolution_note` | text nullable | Admin napomena pri zatvaranju |
| `created_at` | timestamp UTC | |
| `resolved_at` | timestamp UTC nullable | |

> V1 baseline after Phase 10: u jednom trenutku smije postojati najviše jedan `OPEN` report po `normalized_term`. Ta jedinstvenost se provodi parcijalnim unique indeksom nad otvorenim prijavama.

---

### 25. SystemConfig (Sistemske postavke)

Persistira sve konfiguracijske postavke instalacije koje nisu pokrivene postojećim entitetima. Key-value model s tipiziranim vrijednostima.

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `key` | string UNIQUE | Ključ postavke (npr. `default_language`, `barcode_format`) |
| `value` | string | Vrijednost (uvijek string; parsira se prema kontekstu) |
| `updated_at` | timestamp UTC | |

Seeded ključevi pri prvom pokretanju:

| Key | Default vrijednost | Opis |
|-----|--------------------|------|
| `default_language` | `hr` | Defaultni jezik UI-a (`hr` / `en` / `de` / `hu`) |
| `barcode_format` | `Code128` | Format barkoda (`EAN-13` / `Code128`) |
| `barcode_printer` | `""` | Naziv printera u OS-u Pi-a |
| `export_format` | `generic` | Format Excel exporta (`generic` / `sap`) |

> `Location.timezone` i `Location.name` ostaju na Location entitetu — pokrivaju "general" settings zajedno s ovim ključevima.

Runtime-managed ključevi:

| Key | Primjer vrijednosti | Opis |
|-----|---------------------|------|
| `order_number_next` | `43` | Sljedeći slobodni numeric suffix za auto-generirani `ORD-####` niz. Održava ga backend Orders servis; nije user-facing postavka. |

---

### 26. RoleDisplayName (Prikaz naziva rola)

Konfigurabilni nazivi sistemskih rola per instalacija. Pet fiksnih redova (jedan po roli).

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | int PK | |
| `role` | enum UNIQUE | `ADMIN` / `MANAGER` / `WAREHOUSE_STAFF` / `VIEWER` / `OPERATOR` |
| `display_name` | string | Naziv koji se prikazuje u UI-u (max 50 znakova) |

Seeded pri prvom pokretanju s defaultnim nazivima iz `03_RBAC.md`.

---

### 27. Supplier (Dobavljač) — CRUD u Settings

> Entitet je isti kao u §1. Napomena: kreiranje i uređivanje dobavljača odvija se u **Settings → Dobavljači** sekciji. Warehouse/Article detail prikazuje dobavljače artikla (read), ali CRUD je isključivo u Settingsima.

---

## Ključna poslovna pravila u modelu

1. **Stock nikad < 0** — CHECK constraint na `stock.quantity`
2. **Surplus-first konzumacija** — pri approval, prvo troši surplus pa stock
3. **FEFO za šarže** — izlaz uvijek konzumira šaržu s najbližim expiry datumom
4. **batch_id je nullable** — artikli bez `has_batch` nemaju šaržu; NULL `batch_id` je validan na svim entitetima (Stock, Surplus, Draft, Transaction, Receiving, InventoryCountLine, PersonalIssuance)
5. **Prosječna cijena** — weighted average, izračunava se automatski pri svakom prijemu
6. **Audit trail** — svaka promjena stocka kreira Transaction zapis
7. **Idempotency** — Draft create prima `client_event_id`, duplikati se ignoriraju
8. **Batch expiry mismatch** — pri prijemu, ako batch već postoji s drugačijim expiry datumom → 409 error
9. **Reorder threshold** — ručni unos pri kreiranju artikla; sustav može predložiti update baziran na prosječnoj potrošnji × `reorder_coverage_days`
10. **Kvota prioritet** — pri provjeri godišnje kvote: override po zaposleniku + artiklu > override po artiklu > default po job_title + kategoriji

---

## Što nije u data modelu v1

- MES entiteti (WorkOrder, ProductionPhase, PieceScan...)
- Multi-tenant podrška
- Remote access / audit log pristupa
- Billing / licenciranje
