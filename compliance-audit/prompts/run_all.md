# Running the Full Audit with Subagents

For large frameworks with many control families, run one subagent per family in parallel
rather than auditing all families sequentially in a single context window.

## Pattern

Open your AI agent and run the following prompt once per family. Each subagent gets its
own context and produces one result file under `audits/{FRAMEWORK}/results/`.

```
Audit the {FAMILY} control family for the {FRAMEWORK} framework.
Follow the instructions in: prompts/template.md
Replace {FAMILY} with: AM
Replace {FRAMEWORK} with: c5
```

## Framework-specific runbooks

Each framework has its own runbook with the correct family list, suggested sequence,
and framework-specific paths. Use those instead of this file when running an audit:

- C5: `audits/c5/run_all.md`
- ISO 27001:2022: `audits/iso27001/run_all.md`

## Adding a new framework

1. **Create the directory structure**
   ```bash
   mkdir -p audits/{framework}/reqs audits/{framework}/results
   touch audits/{framework}/mapping.csv
   echo "family,control,source_type,link,status,doc_type" > audits/{framework}/mapping.csv
   ```

2. **Create `audits/{framework}/families.json`**
   Map family codes to display names. Two conventions are supported:
   - **Native codes with hyphens** (e.g. C5: `"AM"`, `"IDM"`): extracted from `externalId` prefix before `-`.
   - **Dot-notation** (e.g. ISO 27001: `"A.5"`, `"C.6"`): extracted from control name prefix. Use this when the standard organises controls by section number.

   Use `collect_controls.py` to inspect what the API returns before deciding:
   ```bash
   python -m integrations.vanta.collect_controls --framework {id}
   ```

3. **Scaffold req files** (optional, edit placeholders afterwards)
   ```bash
   python -m integrations.vanta.generate_req --framework {id} --output-dir audits/{framework}/reqs
   ```

4. **Create `audits/{framework}/run_all.md`**
   Copy an existing runbook and update:
   - The family list (must match the keys in `families.json` - these are duplicated on purpose for readability, add a comment noting that)
   - The suggested sequence
   - The framework ID in the example prompt
   - The result paths

5. **Add the framework to this file** under "Framework-specific runbooks" above.

## Interpreting scores

- 8-10: adequately evidenced. Verify recency if dates are missing.
- 4-7: partial gaps. Prioritize remediation based on control criticality.
- 0-3: significant gaps. High priority.
- N/A (needs_manual_fetch): fetch the document, save as `.txt` in `docs/{FAMILY}/`,
  update `mapping.csv` status to `ready`, and re-run the affected family.
