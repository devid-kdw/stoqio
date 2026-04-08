# Paint Mixing Demo Setup Report

## Demo account

- Username: `demo_operator`
- Password: `!Mitnica9942`
- Role: `OPERATOR`
- Active: `true`
- Password verified against current DB hash: `true`

## Article IDs

- `800074` -> article_id `1`, barcode `2000000000015`
- `800493` -> article_id `2`, barcode `2000000000022`
- `800738` -> article_id `3`, barcode `2000000000039`
- `800048` -> article_id `4`, barcode `2000000000046`
- `800072` -> article_id `5`, barcode `2000000000053`
- `800071` -> article_id `6`, barcode `2000000000060`
- `800050` -> article_id `7`, barcode `2000000000077`

## Batch IDs

- `0156` -> batch_id `1`, article `800048`, barcode `3000000000014`
- `0158` -> batch_id `2`, article `800048`, barcode `3000000000021`
- `1984` -> batch_id `3`, article `800050`, barcode `3000000000038`
- `4567` -> batch_id `4`, article `800071`, barcode `3000000000045`
- `3217` -> batch_id `5`, article `800072`, barcode `3000000000052`
- `6644` -> batch_id `6`, article `800072`, barcode `3000000000069`
- `0032` -> batch_id `7`, article `800074`, barcode `3000000000076`
- `0033` -> batch_id `8`, article `800074`, barcode `3000000000083`
- `0567` -> batch_id `9`, article `800493`, barcode `3000000000090`
- `0568` -> batch_id `10`, article `800493`, barcode `3000000000106`
- `0002` -> batch_id `11`, article `800738`, barcode `3000000000113`

## Coverage

- Missing expected batch codes: none
- `BARCODE_MAP` in `demo.html` is fully populated
- No `article_id: null` or `batch_id: null` entries remain

## Notes

- Batch barkodovi su već postojali u bazi.
- Article barkodovi su na ovom prolazu poravnani kroz postojeći app barcode service, tako da je demo data set konzistentan i u article i u batch sloju.
- Runtime scan lookup u demu prihvaća i `batch_code` key i stvarni spremljeni `batch.barcode`, tako da demo ostaje praktičan i za tipkanje i za stvarni scan.
