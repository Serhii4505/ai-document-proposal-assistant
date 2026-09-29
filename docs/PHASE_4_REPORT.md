# Phase 4 Verification Report

**Project:** AI Document & Proposal Assistant  
**Date:** 2026-09-28  
**Result:** Passed

## DONE

- Strict approved-catalogue import from UTF-8 CSV and single-sheet XLSX.
- Required-column, duplicate-code and single-currency validation.
- Deterministic `Decimal` pricing with `ROUND_HALF_UP` monetary rounding.
- Catalogue-owned unit prices; AI/request input supplies only service codes and quantities.
- Active-service and minimum-quantity enforcement.
- Named configurable volume discount applied before VAT.
- Configurable VAT, default 23%.
- Exact line, subtotal, discount, taxable, tax and total records.

## DECISIONS

- EUR remains the MVP catalogue currency.
- Default discount rule: `volume_10_percent`, 10% at subtotal EUR 3,000.00.
- Duplicate requested service codes are rejected instead of silently merged.
- Money is rounded to cents with `ROUND_HALF_UP`.
- Unknown, inactive, inconsistent or malformed catalogue data fails closed.

## CURRENT STATE

Phases 1–4 are complete. The system can ingest and retrieve approved evidence and calculate authoritative proposal totals without allowing AI-generated prices.

## VERIFIED RESULTS

- 45 automated tests passed, including all earlier regression tests.
- CSV and XLSX catalogue imports passed.
- VAT, discount ordering and half-up rounding matched expected totals.
- Unknown/inactive services, low quantities, duplicate codes, invalid prices and mixed currencies were rejected.
- Compilation and secret scan passed.

## NEXT STEP

Phase 5: generate an English commercial proposal from validated evidence and pricing results, create DOCX and PDF outputs, and verify that both formats contain identical authoritative totals.

## BLOCKERS

None.

