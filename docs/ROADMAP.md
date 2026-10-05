# Roadmap (after v1)

Ideas that are out of scope for v1 land here instead of in the code.
Roughly in order of value to a Medicare Advantage insurer:

1. **HCC hierarchies and RAF calculation** (V28), showing the payment impact of
   each supported or unsupported code.
2. **Audit packet export:** a PDF per note listing each HCC, its evidence,
   MEAT, reviewer, and timestamp.
3. **Second-level review:** a senior coder or auditor reviews another coder's
   decisions.
4. **Retrieval improvements:** the ICD-10-CM alphabetic index, embeddings with
   pgvector, and hybrid ranking.
5. **Statistical confidence calibration** trained on reviewer decisions.
6. **Personal history Z codes** and refined symptom coding.
7. **More input types:** PDF and scanned notes, FHIR `DocumentReference`.
8. **Hosted version for real use:** a HIPAA-eligible AI provider with a
   Business Associate Agreement, encryption, SSO, and organization accounts.
9. **CPT/E/M module** (requires an AMA license) and an inpatient mode.

Also explicitly out of scope for v1: public hosting, inpatient rules, DRGs,
EHR/FHIR integration, multiple organizations, SSO, local LLMs.
