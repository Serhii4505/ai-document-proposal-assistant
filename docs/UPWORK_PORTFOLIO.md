# Upwork Portfolio Copy

## Title

AI Document & Proposal Assistant — RAG, FastAPI, n8n

## Short description

Portfolio demo of an AI-assisted proposal workflow that extracts approved business information from PDF, DOCX, XLSX and CSV files, retrieves evidence with source references, calculates prices with deterministic Python rules, generates matching DOCX/PDF proposals and requires manager approval through n8n.

## Full description

I built this end-to-end portfolio demonstration to show how AI-assisted document automation can remain controlled, traceable and safe.

The system validates and parses PDF, DOCX, XLSX and CSV files, normalizes their content and indexes source-aware chunks in a local vector database. A request retrieves relevant evidence, while Python validates service codes and independently calculates subtotal, discount, configurable VAT and total using Decimal arithmetic. The application then creates a styled English proposal in DOCX and PDF.

An n8n workflow sends the protected draft to a manager. Approve and Reject actions are stored transactionally in SQLite, repeated actions are idempotent, conflicting decisions return HTTP 409, and no document is sent automatically to a real client.

The project includes 62 automated tests, a 12-criterion acceptance matrix, failure-recovery checks and an automated scan for secrets, personal email addresses and unsafe n8n export metadata.

This is a fictional portfolio project, not a commercial client engagement.

## Skills and deliverables

- Python, FastAPI and Pydantic
- n8n workflow automation
- RAG and vector retrieval
- PDF, DOCX, XLSX and CSV processing
- SQLite persistence and audit trail
- deterministic pricing with Decimal
- DOCX/PDF proposal generation
- Gmail manager notification
- API, security and integration testing

## Suggested gallery order

1. `architecture.png` — system architecture.
2. `proposal-preview.png` — evidence-backed proposal and authoritative total.
3. `approval-workflow.png` — manager approval and idempotency flow.

## Suggested project URL

Add the GitHub repository URL only after Sergey approves publication and the repository is live.

## Suggested completion date

September 2026

## Accuracy note

Do not label this as paid client work, production deployment, CRM integration, automatic client delivery, OCR, electronic signature or payment automation.
