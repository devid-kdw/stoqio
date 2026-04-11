# Warehouse Six-Month Simulation

Ovaj folder sadrzi standalone demo skriptu za STOQIO koja puni zaseban,
deterministicki 6-mjesecni scenarij kretanja robe bez izmjena glavnog
`backend/app` ili `frontend/src` koda.

Sada postoje dvije varijante:

- `simulate_warehouse_six_months.py`
  koristi synthetic demo artikle
- `simulate_real_articles_to_today.py`
  read-only ucita stvarne artikle iz source baze i klonira ih u izoliranu
  target bazu gdje odradi simulaciju do danasnjeg datuma
  takoder podrzava `--in-place` mod za direktan upis u presentation bazu

## Sto radi synthetic mode

- kreira 14 demo artikala unutar zasebnog namespacea
- dodaje 2 zaposlenika:
- `Pero Perić`
- `Ivan Ivanović`
- kreira 6 uzastopnih narudzbi s brojevima:
- `260001`
- `260002`
- `260003`
- `260004`
- `260005`
- `260006`
- provodi linked receiving, redovni outbound kroz draft/approval workflow i
  osobna izdavanja zaposlenicima
- na kraju validira da demo set od 14 artikala zavrsi ovako:
- `3` crvena zona
- `5` narancasta zona
- `6` zelena zona

Detaljnije poslovne pretpostavke i scenarij su u
`20_DEMO_WAREHOUSE_SIX_MONTH_SIM.md`.

## Real DB Clone Mode

Ova varijanta je sigurna za postojece podatke jer:

- source PostgreSQL baza se koristi samo read-only
- simulacija pise iskljucivo u zasebnu target bazu
- rjesava problem retroaktivnih kretanja tako da ne dira postojeci audit trail
- koristi stvarne artikle iz source baze kao article master
- trenutno za `wms_dev` validira rezultat:
- `2` crvena
- `3` narancasta
- `5` zelena
- dodaje 2 zaposlenika u target clone:
- `Pero Perić`
- `Ivan Ivanović`
- kreira 6 narudzbi s brojevima `260001` do `260006`

Primjer pokretanja za stvarne artikle iz lokalnog `wms_dev` i simulaciju koja
zavrsava na `2026-04-11`:

```bash
backend/venv/bin/python \
  standalone-demos/warehouse-six-month-sim/simulate_real_articles_to_today.py \
  --end-date 2026-04-11 \
  --json-out /tmp/stoqio_real_articles_sim.json
```

Ako `--target-database-url` ne zadash, skripta sama kreira svjezu SQLite bazu
u `/tmp`.

Za direktan presentation run u stvarnoj bazi nakon pripremljenog baselinea:

```bash
backend/venv/bin/python \
  standalone-demos/warehouse-six-month-sim/simulate_real_articles_to_today.py \
  --in-place \
  --end-date 2026-04-11 \
  --json-out /tmp/stoqio_real_articles_in_place.json
```

## Vazna napomena

Skripta je namjerno namijenjena zasebnoj demo ili test bazi.

Rezervira fiksne brojeve narudzbi `260001` do `260006`. Ako oni vec postoje,
skripta ce se zaustaviti umjesto da dira postojeci dataset.

## Pokretanje

Iz korijena repoa:

```bash
backend/venv/bin/python \
  standalone-demos/warehouse-six-month-sim/simulate_warehouse_six_months.py \
  --database-url sqlite:////tmp/stoqio_six_month_sim.db \
  --json-out /tmp/stoqio_six_month_sim.json
```

Ako `--database-url` izostavis, koristi se standardni `DATABASE_URL` iz
okoline ili `backend/.env`.

## Rezultat

Skripta ispisuje JSON sa sazetkom scenarija:

- otvoreni prozor simulacije
- kreirane narudzbe
- kreirane zaposlenike
- zavrsne dostupne kolicine po artiklu
- broj artikala po zoni

Opcionalno isti JSON moze zapisati preko `--json-out`.
