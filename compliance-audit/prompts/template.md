# Compliance Audit Prompt Template

Use this prompt in your AI agent (Cursor, Claude, etc.) to audit one control family.
Replace `{FAMILY}` and `{FRAMEWORK}` with the actual values before running.

---

## Prompt

You are a compliance auditor performing a gap analysis for the **{FRAMEWORK}** framework,
control family **{FAMILY}**.

### Inputs

1. **Control checklist**: Read `audits/{FRAMEWORK}/reqs/{family}.md`
   This file defines every control in the family with its ID and requirement text.
   Every control listed here MUST appear in your output table.

2. **Evidence index**: Read `audits/{FRAMEWORK}/mapping.csv` and filter rows where `family = {FAMILY}`.
   Columns: `family`, `control`, `source_type`, `link`, `status`
   - `control` is empty = evidence applies to all controls in the family
   - `control` is filled = evidence applies only to that specific control
   - `status = ready` = local file exists and can be read
   - `status = needs_manual_fetch` = URL-only, content not available locally

3. **Evidence files**: For each row with `status = ready` and `source_type = local_file`,
   read the file at the path in the `link` column.
   For `source_type = confluence`, use your `getConfluencePage` tool if available.
   For `source_type = external_url`, note that manual retrieval is required.

4. **Evidence tiers**: The `doc_type` field is a starting signal, not ground truth. Use it as a hint,
   but always determine the actual content tier by reading the document:

   | Content tier | What it looks like in the document |
   |---|---|
   | **Policy** | States intent, commitments, or requirements ("assets must be…", "the organisation shall…") |
   | **Procedure / Standard** | Defines *how* something is implemented: steps, configuration parameters, checklists, decision trees |
   | **Operational evidence** | Proves the control is *currently operating*: inventory exports, log excerpts, audit reports, dated test results, configuration screenshots, signed attestations |

   A document can contain content from more than one tier — assess and record the highest tier
   actually present in the content, regardless of what `doc_type` says.
   Flag any mismatch between `doc_type` and your content assessment in the Gaps column.

   The scoring ceiling is based on your content assessment, not the `doc_type` field:
   - Only policy-level content present → cap at 4/10
   - Procedure/standard content present but no operational evidence → cap at 6/10
   - Operational evidence present → eligible for 7-10

### Task

For each control in the checklist:

1. Identify all relevant evidence rows from `mapping.csv` (family-level rows + control-specific rows).
2. Read the content of available evidence files.
3. For each document, assess the **highest content tier actually present** (policy / procedure / operational evidence).
4. Assess whether the content directly addresses the control requirement.
5. Score the control on a 0-10 scale, respecting the content-tier ceiling:
   - 0 = no evidence at all
   - 1-3 = policy-level content present but major requirement gaps
   - 4 = maximum when all content is policy-level only (intent stated, implementation unproven)
   - 5-6 = procedure/standard content present but no operational evidence, or content gaps remain
   - 7-9 = operational evidence present and substantially covers the requirement with minor gaps
   - 10 = operational evidence fully and demonstrably covers the requirement
6. Assess whether the evidence is **sufficient and current**:
   - Look for visible dates, version numbers, review dates, or references to superseded standards.
   - If no dates are visible, note that recency cannot be determined.
7. Document any gaps: what is required by the control but not addressed by the evidence.
   - If no operational evidence is present, always add: "No operational evidence — implementation effectiveness unproven."
   - If `doc_type` does not match the content you assessed, note it: "Labeled `{doc_type}` but content is policy-level only."

### Output

Write the results to `audits/{FRAMEWORK}/results/{family}_result.md`.

Use exactly this table format. Every control from the checklist must appear.

```markdown
# {FAMILY} Gap Analysis - {FRAMEWORK}

| Control | Evidence sources | Content assessed as | Evidence sufficient? | Score (0-10) | Gaps |
|---------|-----------------|---------------------|---------------------|--------------|------|
| {FAMILY}-01 | policy.md, inventory-export.csv | Operational evidence | Yes - current (2024), inventory export confirms control is operating | 9/10 | Minor: no automated audit trail |
| {FAMILY}-02 | policy.md, procedure.md | Procedure | Partial - no operational evidence | 6/10 | No operational evidence — implementation effectiveness unproven |
| {FAMILY}-03 | policy.md | Policy only | No - intent stated, nothing more | 4/10 | No operational evidence — implementation effectiveness unproven |
| {FAMILY}-04 | (needs_manual_fetch) | Unknown | Incomplete - Confluence doc not fetched | N/A | Fetch manually and re-run |
| {FAMILY}-05 | (no evidence) | None | No - no docs linked | 0/10 | Link evidence to this control |
```

**Evidence sufficient? column values:**
- `Yes` - operational evidence present, content directly addresses the control, appears current
- `Partial` - procedure/standard content present but no operational evidence, or content does not fully cover the control
- `No` - only policy-level content present (capped at 4/10), or no local content available
- `Incomplete` - `needs_manual_fetch` status; scoring deferred pending manual retrieval

**Important:**
- Do not skip any control from the checklist. If there is no evidence, the row must still appear with score 0/10.
- Controls with `needs_manual_fetch` evidence get `N/A` score and `Incomplete` in the sufficiency column.
- A well-written policy that covers every requirement word-for-word is still capped at 4/10 if the content contains no operational evidence. Policy text states intent, not operational reality — regardless of what `doc_type` says.
- If your content assessment does not match the `doc_type` in the CSV, flag the mismatch in the Gaps column so the mapping can be corrected.
- Scores are a first-pass estimate. A security engineer should validate all scores in the 4-7 range, any control lacking operational evidence, and any control where recency could not be determined.
