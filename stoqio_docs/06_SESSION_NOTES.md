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
