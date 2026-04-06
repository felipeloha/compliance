# AI Compliance Audit Framework

> Blog post: [blog-posts/post-02-ai-compliance-audit.md](../blog-posts/post-02-ai-compliance-audit.md)

We ran our ISO 27001 gap analysis with an AI agent. Here's the prompt pipeline.

## Overview

A modular, provider-agnostic pipeline for AI-assisted compliance gap analysis.

| Component | Role |
|-----------|------|
| `integrations/vanta/` | Downloads evidence from Vanta, converts PDFs to text |
| `audits/{framework}/reqs/` | Control requirement specs in Markdown, one file per family |
| `audits/{framework}/mapping.csv` | Evidence index: source type, link, readiness status |
| `prompts/template.md` | AI audit prompt: reads req file + mapping, outputs gap table |
| `samples/` | Fictional policy docs for zero-credential demo |
| `docs/` | Downloaded evidence files (created by bootstrap, not committed) |

## Architecture

```
Phase 1: Bootstrap (optional, requires Vanta credentials)
  Vanta API → download files → convert PDFs → docs/{FAMILY}/
                              → generate audits/{FRAMEWORK}/mapping.csv

Phase 2: Audit (in your AI agent)
  audits/{FRAMEWORK}/reqs/{family}.md  ─┐
  audits/{FRAMEWORK}/mapping.csv       ─┼─► prompts/template.md → AI → results/{family}_result.md
  docs/{FAMILY}/*.txt                  ─┘

Phase 3: Review
  Engineer reviews result files, commits scores to repo for diff across cycles
```

## Supported frameworks

| Framework | Reqs dir | Status |
|-----------|----------|--------|
| C5 (BSI Cloud Computing Compliance Criteria) | `audits/c5/reqs/` | 17 families |
| ISO 27001:2022 | `audits/iso27001/reqs/` | Placeholder - use `generate_req.py` to seed |

## Quick start (demo path, no credentials)

The `samples/` directory contains fictional policy documents for AM, HR, and IDM.
`audits/c5/mapping.csv` has seed rows pointing to them. No Vanta account needed.

```bash
cd compliance-audit
uv sync --group dev

# Run the audit for the AM family in your AI agent:
# 1. Open prompts/template.md
# 2. Replace {FAMILY} with AM and {FRAMEWORK} with c5
# 3. Run in Cursor or Claude with access to the repo files
# Results land in audits/c5/results/am_result.md
```

Check mapping completeness before auditing:

```bash
grep needs_manual_fetch audits/c5/mapping.csv
```

Rows returned = controls with URL-only evidence. They score N/A until fetched manually.

## Configuration (Vanta bootstrap path)

Copy and fill in the env file:

```bash
cp integrations/vanta/.env.example integrations/vanta/.env
```

| Variable | Description |
|----------|-------------|
| `COMPLIANCE_TOOL` | Integration to use (default: `vanta`) |
| `VANTA_CLIENT_ID` | Vanta OAuth client ID |
| `VANTA_CLIENT_SECRET` | Vanta OAuth client secret |
| `VANTA_FRAMEWORK_ID` | Framework to fetch (default: `iso27001_2022`) |
| `VANTA_APP_URL` | Vanta app base URL (default: `https://app.vanta.com`) |
| `CONFLUENCE_BASE_URL` | Your Confluence base URL (for manual fetch references) |

## Phase 1: Bootstrap

```bash
# Fetch all controls, download evidence, build mapping.csv
python -m integrations.vanta.bootstrap \
  --framework iso27001_2022 \
  --docs-dir docs \
  --mapping-file audits/c5/mapping.csv
```

Downloads uploaded files, converts PDFs to `.txt`, records URL-only documents as
`needs_manual_fetch`. Non-destructive: reruns add new rows without overwriting manual edits.

### Exporting the control inventory

```bash
# Read-only inventory export (no file downloads)
python -m integrations.vanta.collect_controls \
  --framework iso27001_2022 \
  --output-csv controls.csv

# Include linked document metadata
python -m integrations.vanta.collect_controls \
  --framework iso27001_2022 \
  --include-docs \
  --output-csv controls.csv \
  --output-json controls.json
```

## Phase 2: Audit

Run one family at a time in your AI agent. See `prompts/template.md` for the full prompt.

For large frameworks, run families in parallel using separate subagent contexts.
See `prompts/run_all.md` for the recommended sequence and subagent pattern.

## Phase 3: Review

Result files land in `audits/{FRAMEWORK}/results/`. Commit them to track gap scores
across audit cycles:

```bash
git add audits/c5/results/
git commit -m "audit: c5 gap analysis $(date +%Y-%m)"
```

## Tests

```bash
# All tests
uv run pytest tests/ -v

# Mapping integrity only (no credentials needed)
uv run pytest tests/test_mapping.py -v
```

## Adding a new control family

1. Copy `audits/c5/reqs/TEMPLATE.md` to `audits/c5/reqs/{family}.md`
2. Fill in `# {FAMILY} - {Name}` header and `## {ID} {Control name}` sections
3. Add evidence rows to `audits/c5/mapping.csv`
4. Run `uv run pytest tests/test_mapping.py -v` to verify

## Adding a new compliance framework

1. Create `audits/{framework}/reqs/` and `audits/{framework}/results/` directories
2. Add req files for each control family (or use `generate_req.py` to seed from Vanta)
3. Create `audits/{framework}/mapping.csv` with headers
4. Run bootstrap with `--mapping-file audits/{framework}/mapping.csv`
