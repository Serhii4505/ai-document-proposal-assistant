# Phase 6 Report — n8n Orchestration and Manager Approval

Date: 2026-09-28; local acceptance completed 2026-09-29

## DONE

- Extended the existing Phase 1–5 project without recreating previous work.
- Added `POST /api/v1/requests` to validate a request, apply the approved Python pricing rules, generate DOCX/PDF drafts and persist `pending_approval`.
- Added protected DOCX/PDF download endpoints. A runtime review token is returned to n8n; SQLite stores only its SHA-256 hash.
- Added proposal status and protected audit-event endpoints.
- Added manager `approve` and `reject` actions. Rejection requires a comment.
- Added transactional SQLite tables for workflow requests, workflow proposals, manager decisions and workflow events.
- Added idempotency: the same decision is replay-safe and creates one decision/event; a reused key for another operation or an opposite decision returns HTTP 409.
- Added clear 4xx result payloads for missing proposals, invalid tokens, validation/pricing failures, unavailable drafts and decision conflicts.
- Added a sanitized, inactive n8n workflow export with request, success/error, manager notification, approval and rejection branches.
- Confirmed there is no client-delivery node and no automatic approval path.

## DECISIONS

- FastAPI and SQLite are authoritative for pricing, status, approval and the audit trail. n8n only orchestrates calls and manager notification.
- A newly generated proposal is always `pending_approval`; `can_finalize` is true only for `approved`.
- Review tokens are never stored in plaintext. Public n8n JSON contains environment-variable references only and no credentials.
- Approve/Reject are POST actions. Email links expose only protected draft downloads; a click cannot mutate proposal state.
- The demo stops after the manager decision. No real client email is sent.

## TEST RESULTS

- Full automated suite: **57 passed**.
- Positive cases: draft creation, protected PDF retrieval, approval, rejection, status retrieval, audit retrieval and same-action replay.
- Negative cases: invalid token, rejection without comment, opposite decision, cross-proposal idempotency-key reuse, unknown service and protected audit access.
- Database assertions verified one decision and one audit event after repeated approval calls.
- Real generator smoke test created a valid 77,735-byte PDF, moved from `pending_approval` to `approved`, returned `can_finalize=true` and recorded two proposal events.
- Python compilation and n8n JSON parsing passed.
- Security scan found no stored API key, credential block, real email address or client-delivery node in the n8n export.

## CURRENT STATE

Phase 6 implementation, automated verification and the full local n8n/Gmail acceptance scenario are complete. On Sergey's Windows laptop, FastAPI and n8n generated proposal `8412056f-e726-4bc3-b417-f1c23516b3bd` with `pending_approval`; Gmail delivered the protected draft to the manager; the PDF opened and showed the expected confirmed fact and authoritative EUR 1,845.00 total. The first Approve returned `approved`, `can_finalize=true` and `idempotent_replay=false`. Repeating the identical Approve returned `idempotent_replay=true` with the original decision timestamp. A subsequent Reject returned HTTP 409 with `decision_conflict` because the proposal was already approved. SQLite contained status `approved`, exactly one manager decision and exactly two proposal events: `draft_generated` and `manager_approve`. No real client delivery occurred.

The final scratch regression run after the Windows LibreOffice discovery fix remained **57 passed**. The Windows converter now checks the standard `Program Files` LibreOffice path when `soffice` is not on `PATH`, while the isolated LibreOffice profile uses a valid `Path.as_uri()` URI.

## NEXT STEP

Sergey reviews and accepts this completed Phase 6 local verification. Do not start Phase 7 until that explicit acceptance and its scope are agreed.

## BLOCKERS

- No implementation or local-verification blocker remains.
- Phase 7 remains intentionally gated by explicit user acceptance.
