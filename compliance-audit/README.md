# AI Compliance Audit Framework

> Blog post: [blog-posts/post-02-ai-compliance-audit.md](../blog-posts/post-02-ai-compliance-audit.md)

We ran our ISO 27001 gap analysis with an AI agent. Here's the prompt pipeline.

## Overview

Prompt pipeline for AI-assisted compliance gap analysis:

- `.req` spec files for per-domain control requirements
- Per-domain prompts for structured gap scoring (0-10)
- MCP orchestration integrating Vanta and Confluence
- Results committed back as code

## Configuration

Copy the example env file and fill in your credentials:

```bash
cp integrations/vanta/.env.example integrations/vanta/.env
```

| Variable | Description |
|---|---|
| `VANTA_CLIENT_ID` | Vanta OAuth client ID |
| `VANTA_CLIENT_SECRET` | Vanta OAuth client secret |
| `VANTA_FRAMEWORK_ID` | Framework to audit (default: `iso27001_2022`) |
| `VANTA_APP_URL` | Vanta app base URL (default: `https://app.vanta.com`) |
| `CONFLUENCE_BASE_URL` | Your Confluence base URL (for manual fetch references) |

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd compliance-audit
uv sync --group dev
```

## Usage

**Phase 1 - Bootstrap** (run before each audit cycle):

```bash
uv run python -m integrations.vanta.bootstrap --framework iso27001_2022
```

This fetches all controls from Vanta, downloads uploaded evidence files, converts PDFs to `.txt`, and writes `mapping.csv`. URL-only documents (Confluence, external) are recorded with `status=needs_manual_fetch`.

Check completeness before auditing:

```bash
grep needs_manual_fetch mapping.csv
```

**Phase 2 - Audit** (per control family, in your AI agent):

```
Audit the AM control family.
Files: reqs/am.req, mapping.csv (filter family=AM), docs/AM/*.txt
Prompt: prompts/template.md
```

Results are written to `results/{family}_result.md`.

## Tests

```bash
uv run pytest tests/test_vanta_client.py -v
```
