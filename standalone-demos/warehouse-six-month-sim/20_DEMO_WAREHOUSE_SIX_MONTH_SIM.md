# 20_DEMO_WAREHOUSE_SIX_MONTH_SIM

## Svrha

Ovaj demo sluzi za deterministicku simulaciju 6 mjeseci kretanja artikala u
skladistu, bez izmjena STOQIO aplikacijskog codebasea. Sve se nalazi unutar
`standalone-demos/warehouse-six-month-sim/`.

Trenutno postoje dva moda:

- synthetic demo artikli
- real-DB clone mode koji ucita stvarne artikle iz source baze, ali pise samo u
  izoliranu target bazu

## Poslovna pravila koja skripta postuje

- ulaz robe ide kroz order + receiving tok
- izlaz robe za redovne potrebe ide kroz draft group + approval tok
- approval trosi `surplus` prije `stock`
- osobna izdavanja zaposlenicima odmah umanjuju stanje i stvaraju
  `PERSONAL_ISSUE` transakcije
- reorder zona se racuna nad ukupno dostupnim stanjem: `stock + surplus`
- batch artikli koriste eksplicitno zadani batch pri receiptu i outboundu

## Ciljani rezultat scenarija

- ukupno `14` artikala
- zavrsna raspodjela zona:
- `3` crvena
- `5` narancasta
- `6` zelena
- narudzbe imaju fiksne brojeve:
- `260001`
- `260002`
- `260003`
- `260004`
- `260005`
- `260006`
- zaposlenici:
- `Pero Perić`
- `Ivan Ivanović`

Real-DB clone mode trenutno cilja raspodjelu za stvarnih `10` artikala iz
`wms_dev`:

- `2` crvena
- `3` narancasta
- `5` zelena

## Struktura simulacije

Vremenski prozor:
- pocetak `2025-10-03`
- kraj `2026-03-25`

Dogadaji po mjesecu:
- kreiranje narudzbe
- linked receiving
- outbound draft grupa i admin approval
- osobna izdavanja za safety-equipment artikle

## Artefakti

- `simulate_warehouse_six_months.py`:
  standalone runner koji podize app context, puni demo podatke i ispisuje
  zavrsni JSON sazetak
- `simulate_real_articles_to_today.py`:
  standalone runner koji read-only ucita stvarne artikle iz source baze,
  klonira ih u izoliranu bazu i tamo simulira 6 mjeseci do zadanog end date-a
- `README.md`:
  kratke upute za pokretanje

## Napomena za buduci rad

Ako budemo dalje razvijali scenarij, najbolje je zadrzati isti pristup:
prosirivati logiku unutar standalone skripte i ne mijenjati `backend/app` ni
`frontend/src`.
