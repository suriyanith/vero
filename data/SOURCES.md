# External data sources

Raw files live in `data/raw/` (gitignored). Only small fixture extracts are
committed under `data/fixtures/`. For every downloaded file, record the URL,
download date, and SHA-256 here before loading it.

| Data | Source | URL | Downloaded | SHA-256 | License |
|---|---|---|---|---|---|
| ICD-10-CM FY2027 order file (code descriptions) | CMS ICD-10 page | _(fill in)_ | _(fill in)_ | _(fill in)_ | Public domain |
| ICD-10-CM FY2027 tabular list (XML) | CMS / CDC NCHS | _(fill in)_ | _(fill in)_ | _(fill in)_ | Public domain |
| ICD-10 → CMS-HCC V28 mapping | CMS risk adjustment page | _(fill in)_ | _(fill in)_ | _(fill in)_ | Public domain |

Compute a checksum with: `shasum -a 256 <file>`.

CPT is licensed by the AMA and is out of scope — no CPT content may be added
to this repository.
