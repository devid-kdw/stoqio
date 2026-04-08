# Paint Mixing Demo

Ovaj folder je izdvojeni demo artefakt za STOQIO prezentaciju. Nije mijenjan postojeći frontend ni backend kod.

## Sadržaj

- `demo.html` — standalone paint mixing simulator
- `demo.js` — runtime logic extracted from HTML because STOQIO CSP blocks inline scripts
- `20_DEMO_PAINT_MIXING.md` — primary knowledge file for future agents
- `demo-setup-report.md` — resolved live IDs, barcodes, and demo account snapshot

## Kako ga koristiti

1. Posluži `demo.html` na istom originu kao STOQIO API.
2. Najjednostavniji deployment za lokalni/live demo:
   - kopirati `demo.html` u `backend/static/demo.html`
   - otvoriti `http://<stoqio-host>/demo.html`
3. U drugom tabu otvoriti `http://<stoqio-host>/approvals`

## Napomena

`DEMO_CONFIG.stoqio_base_url` ostaje `/api/v1` namjerno, jer demo treba ići same-origin prema STOQIO backendu da ne zapne na CORS-u.

Detaljni resolved podaci i DB status su u `demo-setup-report.md`.
