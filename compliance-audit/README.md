# AI Compliance Audit Framework

> Blog post: [blog-posts/post-02-ai-compliance-audit.md](../blog-posts/post-02-ai-compliance-audit.md)

I built this to automate compliance gap analysis using an AI agent. The core idea: give the agent local evidence files and a control checklist, get back a scored gap table.

Provider-agnostic. Framework-agnostic. The Vanta integration is one way to populate evidence — the audit pipeline itself has no dependency on it.

## How it works

Three phases:

1. **Evidence** — collect policy documents and evidence as local `.txt` files, indexed in `mapping.csv`
2. **Audit** — an AI agent reads each document, classifies it into a content tier (policy / procedure / operational evidence), and produces a scored gap table with a ceiling per tier
3. **Review** — a security engineer validates borderline scores and commits results for diff across cycles

The AI only scores what it can read. If evidence is not locally available, the control gets `N/A` — not a guess, not a 0. A policy document that fully covers a control in writing is still capped at 4/10 — the scoring ceiling enforces that intent and operational proof are treated separately.

## Components

| Component | Role |
|-----------|------|
| `audits/{framework}/reqs/` | Control requirement specs in Markdown, one file per family |
| `audits/{framework}/mapping.csv` | Evidence index: source type, link, readiness status |
| `prompts/template.md` | AI audit prompt: reads req file + mapping, outputs gap table |
| `samples/` | Fictional policy docs for zero-credential demo |
| `integrations/vanta/` | Downloads evidence from Vanta, converts PDFs to text |
| `docs/` | Downloaded evidence files (created by bootstrap, not committed) |

## Supported frameworks

| Framework | Reqs dir | Status |
|-----------|----------|--------|
| C5 (BSI Cloud Computing Compliance Criteria) | `audits/c5/reqs/` | 17 families |
| ISO 27001:2022 | `audits/iso27001/reqs/` | Placeholder - use `generate_req.py` to seed |

## Quick start (no credentials needed)

The `samples/` directory contains fictional policy documents for AM, HR, and IDM.
`audits/c5/mapping.csv` has seed rows pointing to them. No Vanta account needed.

```bash
cd compliance-audit
uv sync --group dev
```

Then open `prompts/template.md` in your AI agent (Cursor, Claude Code, etc.), replace `{FAMILY}` with `AM` and `{FRAMEWORK}` with `c5`, and run it. Results land in `audits/c5/results/am_result.md`.

Or use the interactive workflow prompt — it asks which framework and family to audit, then generates the audit instruction automatically:
- `prompts/interactive.md`

Check mapping completeness before auditing:

```bash
grep needs_manual_fetch audits/c5/mapping.csv
```

Rows returned = controls with URL-only evidence. They score `N/A` until fetched manually.

## Architecture

```
Phase 1: Evidence (populate mapping.csv and docs/)
  Option A: Manually add .txt files to docs/{FAMILY}/ and rows to mapping.csv
  Option B: Run bootstrap.py to pull from Vanta automatically

Phase 2: Audit (in your AI agent)
  audits/{FRAMEWORK}/reqs/{family}.md  ─┐
  audits/{FRAMEWORK}/mapping.csv       ─┼─► prompts/template.md → AI → results/{family}_result.md
  docs/{FAMILY}/*.txt                  ─┘

Phase 3: Review
  Engineer reviews result files, commits scores to repo for diff across cycles
```

## Getting started with Vanta

If your evidence lives in Vanta, the bootstrap script automates Phase 1.

**1. Configure credentials**

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

**2. Run bootstrap**

```bash
python -m integrations.vanta.bootstrap \
  --framework iso27001_2022 \
  --docs-dir docs \
  --mapping-file audits/c5/mapping.csv
```

Downloads uploaded files, converts PDFs to `.txt`, records URL-only documents (Confluence pages, external URLs) as `needs_manual_fetch`. Non-destructive: reruns add new rows without overwriting manual edits.

**3. Check coverage**

```bash
grep needs_manual_fetch audits/c5/mapping.csv
```

Fetch the flagged URLs manually, save as `.txt` files in `docs/{FAMILY}/`, and update the row status to `ready`.

**4. Run the audit**

Open `prompts/template.md` in your AI agent, fill in `{FAMILY}` and `{FRAMEWORK}`, and run. Or use `prompts/interactive.md` for a guided flow.

For large frameworks, run families in parallel using separate subagent contexts.
See `prompts/run_all.md` for the recommended sequence and subagent pattern.

**5. Review and commit**

```bash
git add audits/c5/results/
git commit -m "audit: c5 gap analysis $(date +%Y-%m)"
```

Result files diff cleanly across audit cycles — rerun months later to see what improved, what regressed, and what was never remediated.

### Exporting the control inventory (optional)

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

## MCP integrations

If your AI agent has Confluence or Google Drive MCP tools configured, it can resolve
`needs_manual_fetch` documents automatically during the audit — no manual download step
required for those sources.

| `source_type` in mapping.csv | How it gets resolved |
|------------------------------|----------------------|
| `local_file` | Read directly from `docs/{FAMILY}/` |
| `confluence` | Fetched by the agent via Confluence MCP (`getConfluencePage`) |
| `google_drive` | Fetched by the agent via Google Drive MCP |
| `external_url` | Manual retrieval still required |

The agent attempts MCP fetches at audit time and scores the control normally if content
is returned. Controls that still can't be resolved stay `N/A`.

To use this: add your Confluence or Google Drive MCP to your agent's configuration,
then run the audit as normal. No changes to `mapping.csv` or the bootstrap step needed.

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
