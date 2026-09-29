# n8n Phase 6 setup

Import `phase-6-manager-approval.workflow.json` into n8n, then configure:

1. `FASTAPI_BASE_URL` as an n8n environment variable, for example `http://host.docker.internal:8000` when n8n runs in Docker and FastAPI runs on the host.
2. `MANAGER_EMAIL` as an n8n environment variable.
3. Select an existing Gmail credential in **Send Draft to Manager**. The exported workflow intentionally contains no credential identifier or secret.
4. Keep the workflow inactive until the three test webhooks have passed.

The intake webhook calls FastAPI and emails the manager links to the DOCX/PDF draft. The manager actions call separate approve/reject webhooks. FastAPI remains the authority for status, token validation, idempotency and audit history.

The workflow never sends mail to the requester's address. It has no client-delivery node and cannot mark a proposal approved without a manager action.

## Manager action payloads

Approve:

```json
{
  "proposal_id": "UUID returned by intake",
  "review_token": "runtime token returned by FastAPI",
  "manager_name": "Demo Manager",
  "comment": "Approved for demo finalization",
  "idempotency_key": "approve-unique-operation-id"
}
```

Reject (comment is required):

```json
{
  "proposal_id": "UUID returned by intake",
  "review_token": "runtime token returned by FastAPI",
  "manager_name": "Demo Manager",
  "comment": "Please revise the scope",
  "idempotency_key": "reject-unique-operation-id"
}
```
