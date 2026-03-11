# WMS — Session Notes (2026-03-10)

## SAP Export analiza

Analizirani su sljedeći SAP exporti:
- `Inventura.xlsx` — inventurna lista
- `IZLAZ.xlsx` — izlaz materijala
- `ULAZ.xlsx` — ulaz robe (primka)
- `Bestandsreichweite.xlsx` — doseg zaliha (ulaz + izlaz + stanje po artiklu)
- `Izlaz_boja_u_zadnja_3_mjeseca.xlsx` — transakcijski dnevnik izlaza
- `NARUDŽBA.xlsx` — narudžbenica
- `Warenausgang_exp_paint.xlsx` — izlaz boja (filter view)

**Zaključak**: naš data model potpuno pokriva sve SAP kolone. Model je čak bogatiji (batch tracking, expiry, surplus, audit trail po korisniku, delivery_note_number).

### Odluke iz SAP analize

[ODLUKA] **cost_account (Kontocode) — NE dodajemo u v1.**
Razlog: WMS nije financijski sustav. Konto je stvar SAP-a i računovodstva. Može se dodati kao opcionalno konfigurabino polje u budućnosti ako kupac zatreba.

[ODLUKA] **discount_pct (Rabatt %) — NE dodajemo u v1.**
Razlog: u praksi dobavljač šalje fakturu s već uračunatim rabatom. `unit_price` na primci već reflektira finalnu cijenu. Posebno polje za rabat komplicira unos bez stvarne koristi.

---

## Arhitekturalna pitanja — odgovori

### Login i prvi ekran
- Korisnik vidi **login stranicu** odmah pri otvaranju URL-a
- Terminali imaju **desktop shortcut** koji otvara browser direktno na IP adresi Pi-a
- Korisnik ne treba znati IP adresu niti ručno upisivati URL

### JWT token trajanje — po roli
| Rola | Token trajanje |
|------|----------------|
| `OPERATOR` | 30 dana |
| `ADMIN` | 8 sati |
| `MANAGER` | 8 sati |
| `WAREHOUSE_STAFF` | 8 sati |
| `VIEWER` | 8 sati |

Razlog za dugi OPERATOR token: tablet u pogonu je uvijek isti uređaj, nema smisla da se operater svaki dan prijavljuje.

### Struktura projekta — Monorepo (Opcija A)

[ODLUKA] **Monorepo, Flask servira React build.**

```
wms/
  backend/     ← Flask API
  frontend/    ← React, builda se u backend/static/
```

- Flask servira i API i React build
- Jedan proces, jedan port
- Jedan `systemd` servis na Pi-u
- Nema nginxa, nema dodatne konfiguracije
- Jednostavniji deployment za Pi target

### Lokalni Vite proxy target

[ODLUKA] **Za lokalni frontend proxy koristi se `http://127.0.0.1:5000`, ne `http://localhost:5000`.**

Razlog: na macOS-u AirPlay Receiver može bindati port `5000` i presresti `localhost` promet kada se resolva na IPv6 (`::1`). Korištenje `127.0.0.1` uklanja taj konflikt i daje stabilan Phase 1 development setup.

### Phase 2 — lokalna PostgreSQL verifikacija

Nakon Phase 2 agent isporuke ručno je odrađena lokalna PostgreSQL verifikacija na macOS-u (`PostgreSQL 15` preko Homebrew):
- `.env` postavljen na `DATABASE_URL=postgresql://grzzi@localhost/wms_dev`
- kreirana baza `wms_dev`
- `python3 -m flask db upgrade` inicijalno pao s `KeyError: 'formatters'`
- nakon fix-a u `backend/migrations/env.py`, upgrade prošao
- potvrđeno `27` tablica u PostgreSQL-u (`26` entiteta + `alembic_version`)

[ODLUKA] **`backend/migrations/env.py` mora defensivno guardati `fileConfig(config.config_file_name)`.**

Razlog: na nekim Python 3.9/macOS/Xcode setupima Alembic logging config parsiranje ruši `flask db upgrade` s `KeyError: 'formatters'`. Guard s `try/except` uklanja taj problem bez utjecaja na migracije.

---

## Što je sljedeće

Nastavljamo s **arhitekturalnim dokumentom**. Preostala pitanja:
- Folder struktura projekta (detaljna)
- Flask blueprint organizacija po modulima
- React routing i code splitting
- API konvencije (URL struktura, error format, pagination)
- Auth flow (login → JWT → refresh)
- Pi deployment (systemd, autostart, update proces)
- Development workflow (kako razvijati lokalno, kako deployati na Pi)

---

## Phase 4 closure — first-run setup

Phase 4 (`/setup` first-run flow) was completed and revalidated after agent delivery.

### Follow-up fixes applied by orchestrator

- Backend setup creation now reserves the single supported v1 `Location` row and maps DB conflicts to `409 SETUP_ALREADY_COMPLETED`. This closes the race where two concurrent first-run setup requests could otherwise create multiple locations.
- Frontend setup submission now follows the documented network-error pattern for this flow: retry once on network / server failure, then show a full-page retry state if the second attempt also fails.
- Setup-flow docs were updated to clarify non-ADMIN behavior while initialization is still pending: the user is blocked, shown an error, and returned to `/login` instead of being sent into an ADMIN-only `/setup` redirect loop.

---

## Draft Entry follow-up decision (2026-03-11)

User clarification changed the Draft Entry semantics before the next implementation pass:

- line-level `note` is removed from the operator workflow
- a single optional note now belongs to the whole daily draft (`DraftGroup.description`)
- `Employee ID` remains an optional input on new entries
- `Employee ID` is removed from the Draft Entry daily table to free horizontal space for `Description`

Affected docs updated:
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/04_FEATURE_SPEC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/10_UI_APPROVALS.md`

---

## Phase 5 cleanup follow-up (2026-03-11)

External review produced two accepted cleanup items that were implemented after the main Phase 5 closure:

- Draft Entry non-error UI copy was aligned with the global rule: Croatian for normal UI text, English for user-visible errors.
- `DraftGroup.group_number` generation was changed from `DraftGroup.id + 1` to a max existing `IZL-####` suffix approach so visible numbering is not coupled to sparse primary keys.

Revalidation after the cleanup:
- `backend/tests/test_drafts.py` -> 30 passed
- full backend suite -> 77 passed
- frontend lint -> passed
- frontend build -> passed

Recommended note for the next orchestrator:
- do not include `Draft.note` schema removal in the main Phase 6 Approvals prompt
- finish Phase 6 first, then run a dedicated post-Phase-6 schema cleanup for `Draft.note`
- rationale: the approval flow is the last place where any hidden dependency on `Draft` shape could surface, so cleanup is safest immediately after Phase 6, not during it
