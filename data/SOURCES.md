# External data sources

Raw files live in `data/raw/` (gitignored). Only small fixture extracts are
committed under `data/fixtures/` and `backend/tests/fixtures/`. Every
downloaded file is recorded here with URL, download date, and SHA-256.

| Data | File | URL | Downloaded | SHA-256 |
|---|---|---|---|---|
| ICD-10-CM FY2027 code descriptions (order file) | `2027-code-descriptions-tabular-order.zip` → `Code Descriptions/icd10cm_order_2027.txt` | https://www.cms.gov/files/zip/2027-code-descriptions-tabular-order.zip | 2026-10-04 | `91c6c9d1117764ce72375a0f3a5493b1725dafbc1ab283b55799076c9e194965` |
| ICD-10-CM FY2027 tabular list (XML) | `2027-code-tables-tabular-index.zip` → `Table and Index/icd10cm_tabular_2027.xml` | https://www.cms.gov/files/zip/2027-code-tables-tabular-index.zip | 2026-10-04 | `37baa476323714be16f95c9b2c96812bf6f3623d9f15188866e584dc529b0298` |
| ICD-10 → CMS-HCC mappings, payment year 2027 (initial) | `2027-initial-icd-10-cm-mappings.zip` → `2027 Initial ICD-10-CM Mappings.csv` | https://www.cms.gov/files/zip/2027-initial-icd-10-cm-mappings.zip | 2026-10-04 | `71c8bc7c37903024573ec3820bab4a843788acafb715c2c32107d37043f387a2` |
| CMS-HCC V28 model software (HCC labels: `V28115L3.TXT`) | `2027-initial-model-software.zip` → `CMS-HCC software V2826.115.T2.zip` | https://www.cms.gov/files/zip/2027-initial-model-software.zip | 2026-10-04 | `6b021dcd65c053b6c716b470bc47254c03b4fbb08f83d08f3a63805899473bfd` |

All four are CMS publications and public domain. Compute a checksum with
`shasum -a 256 <file>`.

## Download and extract (exact commands)

The Makefile expects these extracted paths. From the repo root:

```bash
cd data/raw
curl -LO https://www.cms.gov/files/zip/2027-code-descriptions-tabular-order.zip
curl -LO https://www.cms.gov/files/zip/2027-code-tables-tabular-index.zip
curl -LO https://www.cms.gov/files/zip/2027-initial-icd-10-cm-mappings.zip
curl -LO https://www.cms.gov/files/zip/2027-initial-model-software.zip
unzip -o 2027-code-descriptions-tabular-order.zip   # -> "Code Descriptions/"
unzip -o 2027-code-tables-tabular-index.zip         # -> "Table and Index/"
unzip -o 2027-initial-icd-10-cm-mappings.zip        # -> mappings CSV
unzip -o 2027-initial-model-software.zip -d model-software
cd model-software && unzip -o "CMS-HCC software V2826.115.T2.zip" -d V28 && cd ..
```

Then `make init` loads everything.

Notes verified against the files on 2026-10-04:

- **Order file layout** (1-indexed columns): 1–5 order number, 7–13 code
  (dotless, left-justified), 15 validity flag (`0` header / `1` billable),
  17–76 short description, 78+ long description.
- **Tabular XML**: `chapter > section > diag` (diags nest); per-diag elements
  `name`, `desc`, `inclusionTerm`, `excludes1`, `excludes2`, `codeFirst`,
  `useAdditionalCode`, `codeAlso`, each containing `note` children.
- **Mappings CSV**: title rows, then a header row (`Diagnosis Code`, …);
  data columns: 0 = dotless code, 1 = description, 6 = CMS-HCC **V28**
  category number (blank = maps to no HCC). The initial PY2027 file covers
  codes valid in FY2025–FY2026; CMS publishes midyear/final updates later.
- **HCC labels**: `V28115L3.TXT` is a SAS LABEL macro with lines like
  `HCC37 ="Diabetes with Chronic Complications "`.

CPT is licensed by the AMA and is out of scope — no CPT content may be added
to this repository.
