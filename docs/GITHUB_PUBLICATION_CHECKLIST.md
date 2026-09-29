# GitHub Publication Checklist

Publication is prepared but **not authorized yet**.

## Recommended repository

- Name: `ai-document-proposal-assistant`
- Visibility: Public
- Description: `RAG-powered proposal automation with FastAPI, n8n, deterministic pricing and manager approval.`
- Topics: `python`, `fastapi`, `n8n`, `rag`, `automation`, `sqlite`, `document-processing`, `proposal-generation`

## Before creating or pushing

- [ ] Sergey confirms the repository name and public visibility.
- [ ] Extract the final Phase 8 archive into a clean folder.
- [ ] Run `python scripts/security_scan.py .`.
- [ ] Run `python -m pytest` and confirm 62 tests pass.
- [ ] Confirm `.env`, local databases, runtime output and credentials are absent.
- [ ] Confirm the n8n workflow is inactive and has blank webhook IDs.
- [ ] Confirm only synthetic names and `example.com` addresses appear.
- [ ] Confirm README images render correctly on GitHub.
- [ ] Confirm no `LICENSE` file is added unless Sergey chooses one.

## Proposed first commit

`Publish AI Document & Proposal Assistant portfolio demo`

## After push

- [ ] Open the public repository in a signed-out/private browser window.
- [ ] Recheck README links and images.
- [ ] Search the public repository for `API_KEY`, `CLIENT_SECRET`, `credentials`, `.env` and real email addresses.
- [ ] Add the verified repository URL to the Upwork portfolio item.

Nothing should be published or pushed until Sergey gives separate confirmation.
