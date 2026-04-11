# 20_DEMO_PAINT_MIXING

## Status

Active repo-local knowledge file for the standalone STOQIO paint-mixing demo.

This file exists so future agents do not need to reconstruct the demo from
chat history, browser screenshots, or the external planning file on the
Desktop. Treat this document as the implementation handoff for the demo that
currently lives in this repo.

## Original source document

The demo was implemented from the external planning document:

- `/Users/grzzi/Desktop/STOQIO IZMJENE/20_DEMO_PAINT_MIXING.md`

An additional external process specification is also relevant for the demo:

- `/Users/grzzi/Desktop/STOQIO IZMJENE/ENAE-PWI-06.pdf`

That external file was read fully before implementation. The most important
sections used during implementation were:

- `3.3` barcode-to-system mapping
- `6.1` scanner-active states
- `8.2` draft submission contract
- `9` demo configuration

The PDF was reviewed afterwards as the authoritative process/mixing table
reference for the supported paint systems.

This repo-local knowledge file does not replace the original concept document;
it explains how that concept was translated into concrete files, data, and
deployment steps inside this repo.

## Additional source: ENAE-PWI-06

`ENAE-PWI-06.pdf` is the manual mixing procedure document and is important
because it confirms the real system-level mixing ratios and, for `346-57`,
the required mixing order.

Relevant PDF pages for the current demo scope:

- page 10: `346-55 TOPCOAT` = `5 : 1 + 20% Water`
- page 11: `346-55 TEXTURE` = `5 : 1 + 10% Water`
- page 12: `346-56 TOPCOAT` = `5 : 1 + 20% Water`
- page 13: `346-56 TEXTURE` = `5 : 1 + 10% Water`
- page 14: `346-57 TOPCOAT` = `6 : 1 + 20% Water`
- page 15: `346-57 TEXTURE` = `6 : 1 + 10% Water`
- page 17-18: `346-65 TOPCOAT` = `4 : 1 + 20% Water`
- page 19: `346-65 TEXTURE` = `4 : 1 + 10% Water`

Important procedural note from the PDF:

- `346-57` explicitly says: `Miješanje po sistemu baza, voda, herter`

That note is important because it confirms the special order already used by
the demo:

- `346-57`: `base -> water -> hardener`
- `346-55`, `346-56`, `346-65`: `base -> hardener -> water`

The PDF tables also confirm that all quantities are expressed in grams, which
matches the demo's internal calculation model before STOQIO submission is
converted to kilograms.

## Current demo vs PDF alignment

The currently implemented demo is aligned with the PDF for the supported
TOPCOAT systems:

- `346-55 TOPCOAT` -> ratio `5:1`, water `20%`
- `346-56 TOPCOAT` -> ratio `5:1`, water `20%`
- `346-57 TOPCOAT` -> ratio `6:1`, water `20%`, special order `base -> water -> hardener`
- `346-65 TOPCOAT` -> ratio `4:1`, water `20%`

The demo now also supports `TEXTURE` as an explicit presenter/operator choice:

- `346-55 TEXTURE` -> ratio `5:1`, water `10%`
- `346-56 TEXTURE` -> ratio `5:1`, water `10%`
- `346-57 TEXTURE` -> ratio `6:1`, water `10%`, special order `base -> water -> hardener`
- `346-65 TEXTURE` -> ratio `4:1`, water `10%`

Important implementation detail:

- batch scan resolves the paint system family (`346-55`, `346-56`, `346-57`, `346-65`)
- presenter selects the recipe variant via visible `TOPCOAT` / `TEXTURE` buttons
- variant selection determines the water percentage and final recipe config
- the selected variant is locked for the active mix after the base scan

## Demo architecture

The demo is intentionally separate from the STOQIO product code.

- It is a standalone static artifact.
- It talks to the live STOQIO API on the same origin.
- It does not add new Flask routes.
- It does not require the Vite frontend bundle.
- It should be treated as a presentation tool, not as product UI.

Current artifact layout:

- `standalone-demos/paint-mixing-live/demo.html`
- `standalone-demos/paint-mixing-live/demo.js`
- `standalone-demos/paint-mixing-live/README.md`
- `standalone-demos/paint-mixing-live/demo-setup-report.md`
- `standalone-demos/paint-mixing-live/20_DEMO_PAINT_MIXING.md`

Deployment copy currently used for live serving:

- `backend/static/demo.html`
- `backend/static/demo.js`

## Important deployment constraint: CSP

This is the most important implementation detail for future agents.

The STOQIO backend sends a CSP that allows inline styles but does **not**
allow inline scripts. Because of that:

- a single-file demo with inline JavaScript will render visually
- but none of the buttons or interactions will work
- the browser silently blocks the inline script

This happened during implementation.

That is why the demo logic was extracted into:

- `standalone-demos/paint-mixing-live/demo.js`
- `backend/static/demo.js`

And the served HTML now loads the script with:

- `<script src="./demo.js" defer></script>`

Future agents should **not** move the runtime logic back into inline
`<script>` inside `demo.html` unless the backend CSP is deliberately changed.

## Current runtime behavior

The demo currently does the following:

1. Logs in to STOQIO on page load using `demo_operator`
2. Lets the presenter choose `TOPCOAT` or `TEXTURE` before base scan
3. Simulates scale behavior and workflow states
4. Accepts scan input for base and hardener only in the correct states
5. Resolves the paint system from the scanned base batch barcode
6. Applies the selected variant to determine the active mixing ratios
7. Calculates hardener and water quantities in grams
8. Submits two STOQIO draft lines after countdown:
   - base
   - hardener
9. Does not submit water

The API contract used is:

- `POST /api/v1/auth/login`
- `POST /api/v1/drafts`

Submission details:

- demo works internally in grams
- STOQIO submission is in kilograms
- conversion used is `grams / 1000`
- payload uses `source: "manual"`
- both lines share a UUID prefix in `client_event_id`
- `draft_note` format is `Demo: <system> <variant>`

## Live demo account

The current demo account in the local/live STOQIO instance is:

- username: `demo_operator`
- password: `!Mitnica9942`
- role: `OPERATOR`

During implementation this account was verified against the running API and
against the current DB hash.

## Resolved live article data

The demo was wired against the local STOQIO PostgreSQL data set used during
implementation.

Resolved article IDs:

- `800074` -> `article_id=1`
- `800493` -> `article_id=2`
- `800738` -> `article_id=3`
- `800048` -> `article_id=4`
- `800072` -> `article_id=5`
- `800071` -> `article_id=6`
- `800050` -> `article_id=7`

Resolved batch IDs:

- `0156` -> `batch_id=1`
- `0158` -> `batch_id=2`
- `1984` -> `batch_id=3`
- `4567` -> `batch_id=4`
- `3217` -> `batch_id=5`
- `6644` -> `batch_id=6`
- `0032` -> `batch_id=7`
- `0033` -> `batch_id=8`
- `0567` -> `batch_id=9`
- `0568` -> `batch_id=10`
- `0002` -> `batch_id=11`

Expected batch coverage was complete at implementation time. No expected batch
codes were missing.

## Barcode state at implementation time

### Batch barcodes

Batch barcodes already existed in the database and were used directly for the
demo mapping.

### Article barcodes

At implementation time the `article.barcode` field for the 7 demo articles was
observed as `NULL`, even though the user expected barcode data to already
exist. To make the dataset consistent, article barcodes were generated through
the existing STOQIO app service rather than through raw SQL or a custom method.

The service used was:

- `backend/app/services/barcode_service.py`
- `ensure_article_barcode(article_id)`

This preserved the app's canonical generation logic and avoided creating a
parallel barcode scheme.

Generated article barcode values used in the dataset:

- `800074` -> `2000000000015`
- `800493` -> `2000000000022`
- `800738` -> `2000000000039`
- `800048` -> `2000000000046`
- `800072` -> `2000000000053`
- `800071` -> `2000000000060`
- `800050` -> `2000000000077`

## Current BARCODE_MAP behavior

The demo uses real batch barcode values as the primary scan values.

Important detail:

- shortcut buttons simulate the **real stored batch barcode**
- manual text input also accepts the `batch_code` alias key for convenience

That means both of these work:

- real scan of the stored barcode value
- manual typed shortcut like `0156`

This dual behavior is intentional for demos and debugging.

## Files and responsibilities

### `standalone-demos/paint-mixing-live/demo.html`

Purpose:

- static structure
- inline CSS
- same-origin script include
- visible UI shell for the demo

Contains:

- header
- scale display
- instruction panel
- component breakdown
- scanner field
- active session summary
- main action buttons
- demo shortcut panels

### `standalone-demos/paint-mixing-live/demo.js`

Purpose:

- all runtime logic
- API login
- state machine
- quantity calculations
- scan handling
- draft submission
- demo shortcut behavior

This file must remain external because of backend CSP.

### `standalone-demos/paint-mixing-live/demo-setup-report.md`

Purpose:

- records the resolved IDs and barcodes used during wiring
- records demo account status
- records whether BARCODE_MAP was fully populated

### `standalone-demos/paint-mixing-live/README.md`

Purpose:

- short operator/deployment guide

## Workflow implementation notes

The implemented state machine follows the original concept closely.

Core states:

- `IDLE`
- `WAITING_BASE_SCAN`
- `TARE_AFTER_BASE`
- `POURING_WATER_FIRST`
- `TARE_AFTER_WATER`
- `POURING_HARDENER`
- `WAITING_HARDENER_SCAN`
- `HARDENER_WARNING`
- `POURING_WATER_LAST`
- `CONFIRMING`
- `SUBMITTING`
- `SUCCESS`
- `ERROR`

Rules kept from the planning doc:

- scanner only acts in base-scan and hardener-scan states
- base scan determines the whole mixing session
- selected `TOPCOAT` / `TEXTURE` determines the recipe variant for that session
- hardener tolerance uses 10%
- water is informational and never submitted to STOQIO
- `346-57` uses `base -> water -> hardener`
- the other supported systems use `base -> hardener -> water`

## Demo usability additions that were implemented

These are not just from the original concept doc; they were added during
practical demo preparation.

### 1. Scan shortcut buttons

Because the number of demo batches is small, the demo now exposes direct
buttons for every base and hardener batch used in the presentation.

Purpose:

- avoid manual typing during presentation
- avoid needing a physical scanner
- make rehearsals faster

### 2. Scale shortcut buttons

The demo now exposes weight simulation buttons:

- base random
- hardener within tolerance
- hardener outside tolerance
- water
- reset to zero

Purpose:

- reduce presenter friction
- avoid waiting through animated pour flow when rehearsing
- make tolerance handling easy to demo on demand

### 3. Context-aware shortcut validation

The shortcut buttons do not blindly force invalid transitions.

Examples:

- base shortcut is intended only at the start
- hardener shortcut requires that base has already been scanned
- water shortcut requires a known expected water quantity

This keeps the demo from drifting into nonsensical state.

## Known gotchas for future agents

### 1. Do not assume `demo.html` alone is enough

When serving through STOQIO backend static assets, both files are needed:

- `demo.html`
- `demo.js`

If only `demo.html` is copied, the page will render but interactions will fail.

### 2. If DB data changes, BARCODE_MAP must be refreshed

If any of the following change, the demo must be rewired:

- article IDs
- batch IDs
- batch barcodes
- demo user credentials

The map is intentionally explicit; it is not auto-discovered at runtime.

### 3. Variant is now user-selected, not inferred from batch map

The batch map resolves the paint family/system, but the recipe variant is
selected in the UI through explicit `TOPCOAT` / `TEXTURE` buttons.

Future agents should preserve that separation unless the demo concept is
deliberately changed again.

### 4. Draft submission was smoke-verified via login, not by deliberate bulk seeding

The demo account and auth path were verified against the live API.
The implementation intentionally did not mass-create extra approvals traffic
outside the actual presentation/demo flow.

## How to deploy the current demo

Current simplest deployment:

1. Copy:
   - `standalone-demos/paint-mixing-live/demo.html` -> `backend/static/demo.html`
   - `standalone-demos/paint-mixing-live/demo.js` -> `backend/static/demo.js`
2. Run STOQIO backend
3. Open:
   - `/demo.html`
   - `/approvals`

If you change the demo, recopy both files.

## How to test quickly

Basic fast path:

1. open `/demo.html`
2. click `Baza nasumično`
3. click one base batch shortcut
4. click `Tariranje`
5. depending on system:
   - for `346-57`, do water first
   - otherwise do hardener first
6. use hardener shortcut
7. let countdown submit
8. inspect `/approvals`

## Recommended next polish items

These are the most likely future requests:

- add one-click `Auto demo` flow
- add larger presentation-mode controls
- tune visual polish for projector use
- add explicit system cards for presenter-driven selection/rehearsal
- add a visible "real barcode value copied" helper
- add a tiny debug panel showing current internal state
- support TEXTURE variants if needed by the presentation

## Final note for future agents

If you need to modify this demo:

- treat the external Desktop planning doc as the original concept source
- treat this file as the repo-local implementation source of truth
- keep the demo separate from STOQIO app code unless there is a deliberate
  product requirement to merge it
- remember the CSP restriction before touching the script structure
