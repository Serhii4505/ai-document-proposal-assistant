# Phase 2 Verification Report

**Project:** AI Document & Proposal Assistant  
**Company:** Northstar Automation  
**Date:** 2026-09-28  
**Result:** Passed

## DONE

- Added a dedicated `app.ingestion` package without rebuilding Phase 1.
- Added safe path enforcement with an explicit approved root directory.
- Added extension and file-signature validation for PDF, DOCX, XLSX and CSV.
- Added Office ZIP inspection for unsafe member paths, encryption, member count, expanded size, individual member size and compression-ratio limits.
- Added bounded PDF, DOCX, XLSX and CSV parsers.
- Added Unicode and whitespace normalization without executing source content.
- Added source metadata for PDF pages, DOCX paragraphs/tables, XLSX sheets/rows and CSV rows.
- Added SHA-256 checksums and stable document IDs.
- Added deterministic source-preserving chunks with configurable target size and overlap.
- Added positive and negative automated tests.

## DECISIONS

- OCR remains outside the MVP; image-only PDFs fail with an explicit message.
- CSV input must use UTF-8 or UTF-8 with BOM.
- Supported Office inputs are `.docx` and `.xlsx`; macro-enabled or legacy formats are not accepted.
- Default maximum uploaded file size is 10 MiB.
- Default chunk target is 1,200 characters with 150-character overlap.
- Same file content produces the same document ID and chunk IDs.
- Extracted text remains untrusted data and is never executed or interpreted as instructions.

## VERIFIED RESULTS

- 27 automated tests passed, including all Phase 1 regression tests.
- Valid PDF, DOCX, XLSX and CSV files were parsed successfully.
- Page, paragraph, table, sheet and row source locations were retained.
- Whitespace normalization and deterministic IDs were confirmed.
- Long content was split while retaining source metadata.
- Files outside the approved root and symbolic links were rejected.
- Unsupported extensions and extension/signature mismatches were rejected.
- Empty, oversized, binary/non-UTF-8 and excessive-row inputs were rejected.
- Unsafe Office archive paths and wrong internal Office types were rejected.
- PDF without extractable text was rejected because OCR is intentionally disabled.
- Source compilation completed successfully.

## CURRENT STATE

Phase 2 is complete. The system can safely convert approved local business documents into normalized, traceable chunks ready for embedding and vector indexing. No embedding provider or vector database has been added yet.

## NEXT STEP

Phase 3: add a replaceable embedding adapter, local persistent vector storage, document indexing, top-k retrieval with source metadata, insufficient-evidence behavior and prompt-injection resistance tests.

## BLOCKERS

None. Gemini credentials are not required until the real Gemini embedding adapter is exercised. Tests should continue to use a deterministic local fake adapter so they do not consume API quota.

