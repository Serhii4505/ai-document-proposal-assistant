# Phase 7 Report — Full Testing and Hardening

Date: 2026-09-29

## DONE

- Ran a cross-component acceptance path through PDF/DOCX/XLSX/CSV ingestion, persistent RAG indexing and retrieval, deterministic catalogue pricing, and matching DOCX/PDF generation.
- Added source filenames and extensions to real ingested chunk metadata. This closes a traceability gap found by the new cross-component test; stable document and chunk IDs remain unchanged.
- Added proposal-output cleanup after generation failure. A partial DOCX/PDF directory is removed before the failed status and audit record are stored.
- Added stable machine-readable error codes for proposal generation, pricing-integrity and PDF-conversion failures.
- Added the missing rejected-to-approved conflict test. An approved or rejected decision cannot be reversed by a later opposite action.
- Added a repository-wide public-export scanner for likely secrets, non-demo email addresses, active workflow state, credential blocks, pin data, version IDs and webhook IDs.
- Retained all Phase 1–6 behavior, including client delivery disabled and manager approval required.

## ACCEPTANCE MATRIX

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Valid PDF, DOCX, XLSX and CSV are ingested | Format tests plus complete Phase 7 cross-component path | PASS |
| 2 | Unsupported and corrupt files are rejected safely | Ingestion security and negative-format tests | PASS |
| 3 | Valid request retrieves relevant content with source metadata | Persistent RAG tests and real-ingestion filename metadata assertion | PASS |
| 4 | Prompt injection cannot override system rules | Retrieved content remains JSON-serialized untrusted evidence with explicit instruction boundary | PASS |
| 5 | Prices match independent expected calculations | Decimal catalogue tests and Phase 7 expected subtotal/discount/VAT/total assertions | PASS |
| 6 | Unknown service stops generation | Workflow returns 422, stores `failed`, records audit events and creates no decision | PASS |
| 7 | DOCX/PDF contain matching totals and required sections | Proposal tests and complete Phase 7 generator path | PASS |
| 8 | Proposal remains pending before approval | API/status tests and completed local Phase 6 verification | PASS |
| 9 | Rejected proposal cannot finalize or later approve | Reject state, `can_finalize=false`, and opposite-action HTTP 409 tests | PASS |
| 10 | Duplicate approval creates no duplicate output/decision | Idempotent replay tests, database counts and completed local Phase 6 verification | PASS |
| 11 | Failures return clear status and retain audit record | Unknown-service and partial-PDF-conversion recovery tests | PASS |
| 12 | Public package contains no secrets, credentials or real customer data | Automated tree scan and sanitized inactive n8n-export assertions | PASS |

## TEST RESULTS

- Full suite: **62 passed**.
- Public-export security scan: **passed**.
- Python bytecode compilation: **passed**.
- n8n JSON parsing and structural safety checks: **passed**.
- Release archive integrity: **passed**; 63 public files were extracted successfully.
- Second security scan against the extracted release archive: **passed**.
- One known third-party `StarletteDeprecationWarning` remains non-blocking; it originates in the installed FastAPI/Starlette test client compatibility layer and does not affect runtime behavior or assertions.

## DECISIONS

- No production deployment, CRM, authentication, OCR, payment, electronic signature, multilingual proposal or real-client delivery was added; these remain outside the approved MVP.
- Deterministic Python/SQLite logic remains authoritative for prices, status, decisions and audit history.
- The public n8n export stays inactive and contains only environment-variable references. Local credentials are never copied into the release.
- Phase 7 does not repeat the already completed local Phase 6 Gmail and approval verification.

## CURRENT STATE

Phase 7 implementation and automated acceptance testing are complete. All 12 MVP acceptance criteria have direct evidence. No local Windows or n8n action was required for these hardening changes, and no unconfirmed local check is claimed.

## NEXT STEP

Phase 8 only after Sergey reviews and accepts Phase 7. Phase 8 prepares the English public README, architecture diagram, screenshots/demo outputs, GitHub publication and Upwork portfolio entry.

## BLOCKERS

None for Phase 7.
