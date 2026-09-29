# Phase 3 Verification Report

**Project:** AI Document & Proposal Assistant  
**Company:** Northstar Automation  
**Date:** 2026-09-28  
**Result:** Passed

## DONE

- Added a replaceable embedding adapter interface.
- Added a deterministic offline adapter for tests without API usage.
- Added a Gemini REST adapter with runtime-only API key handling.
- Added persistent SQLite vector storage with normalized vectors.
- Added transactional document replacement and persistent indexing.
- Added cosine-similarity top-k retrieval.
- Added model and dimension isolation so incompatible embeddings are not mixed.
- Preserved chunk text, document ID, source location and source metadata.
- Added an explicit minimum evidence threshold.
- Added safe JSON context serialization that labels all retrieved content as untrusted data.

## DECISIONS

- Local SQLite vector storage is used for the portfolio MVP to keep installation small, transparent and persistent.
- The vector store is behind a dedicated class and can be replaced later.
- `gemini-embedding-2` is the configured live model.
- Documents and queries use different retrieval prefixes recommended for asymmetric retrieval.
- Automated tests never call Gemini and never consume API quota.
- A low-confidence result raises `InsufficientEvidenceError` instead of permitting unsupported proposal content.
- Retrieved instructions are retained as quoted source data but are never promoted to application instructions.

## VERIFIED RESULTS

- 35 automated tests passed, including all Phase 1 and Phase 2 regression tests.
- Relevant indexed content ranked first for a matching query.
- Vector data persisted across store/service instances.
- Reindexing the same document removed obsolete chunks.
- Inconsistent vector dimensions were rejected.
- Insufficient evidence stopped retrieval.
- Prompt-injection text remained inside a clearly labeled untrusted JSON data section.
- Gemini request formatting and safe provider-error handling were verified with a mocked HTTP transport.

## CURRENT STATE

Phases 1–3 are complete. Approved documents can be safely parsed, converted into traceable chunks, indexed locally and retrieved with source metadata. No generative proposal drafting or pricing logic has been implemented yet.

## NEXT STEP

Phase 4: implement the deterministic Decimal-based pricing engine, approved catalogue import, service-code validation, minimum quantities, configurable named discount rule, VAT calculation and exact rounding tests.

## BLOCKERS

None for Phase 4. A real Gemini key is needed only for a later live integration test.

