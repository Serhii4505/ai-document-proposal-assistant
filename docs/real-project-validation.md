# Real Project MCP Validation

This document records practical MCP validation against a real FastAPI/SQLite project.

## Project

Validated against:

`F:\AI_PROJECTS\ai-document-proposal-assistant-final`

The project is an AI Document & Proposal Assistant built with FastAPI, SQLite, document ingestion, RAG, proposal generation, and n8n approval workflows.

## Validation Goals

The purpose of this validation was to confirm that the MCP toolkit works outside the toolkit repository itself.

The checks covered:

- project inspection
- Git status inspection
- safe file listing
- safe text file reading
- path traversal protection
- read-only SQLite access

## project-tools

The `project-tools` MCP server was used to inspect the real project.

Validated tools:

- `project_info(path)`
- `git_status(path)`

Results:

- the project structure was detected successfully
- the Git branch was detected as `main`
- the repository was tracking `origin/main`
- the working tree was clean
- no files were changed

## safe-files

The `safe-files` MCP server was used against the real project root.

Validated tools:

- `list_files(root_path, relative_path)`
- `read_text_file(root_path, relative_path)`

Successful checks:

- listed the project root
- read `README.md`
- returned UTF-8 text correctly
- did not modify files

## Path Traversal Protection

A read attempt was made using:

```text
../MCP_TOOLKIT/README.md