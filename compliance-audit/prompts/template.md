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

### Task

For each control in the checklist:

1. Identify all relevant evidence rows from `mapping.csv` (family-level rows + control-specific rows).
2. Read the content of available evidence files.
3. Assess whether the evidence directly addresses the control requirement.
4. Score the control on a 0-10 scale:
   - 0 = no evidence at all
   - 1-3 = evidence exists but has major gaps
   - 4-6 = evidence partially covers the requirement
   - 7-9 = evidence substantially covers the requirement with minor gaps
   - 10 = evidence fully and demonstrably covers the requirement
5. Assess whether the evidence is **sufficient and current**:
   - Look for visible dates, version numbers, review dates, or references to superseded standards.
   - If no dates are visible, note that recency cannot be determined.
6. Document any gaps: what is required by the control but not addressed by the evidence.

### Output

Write the results to `audits/{FRAMEWORK}/results/{family}_result.md`.

Use exactly this table format. Every control from the checklist must appear.

```markdown
# {FAMILY} Gap Analysis - {FRAMEWORK}

| Control | Evidence sources | Evidence sufficient? | Score (0-10) | Gaps |
|---------|-----------------|---------------------|--------------|------|
| {FAMILY}-01 | filename.txt | Yes - current (2024), covers full requirement | 9/10 | Minor: no automated audit trail |
| {FAMILY}-02 | policy-doc.txt, procedure.txt | Partial - policy exists, no procedure for edge case | 6/10 | Missing exception handling procedure |
| {FAMILY}-03 | (needs_manual_fetch) | Incomplete - Confluence doc not fetched | N/A | Fetch manually and re-run |
| {FAMILY}-04 | (no evidence) | No - no docs linked | 0/10 | Link policy docs to this control |
```

**Evidence sufficient? column values:**
- `Yes` - content directly addresses the control, appears current
- `Partial` - doc exists but does not fully cover the control, or appears outdated
- `No` - no local content available to evaluate
- `Incomplete` - `needs_manual_fetch` status; scoring deferred pending manual retrieval

**Important:**
- Do not skip any control from the checklist. If there is no evidence, the row must still appear with score 0/10.
- Controls with `needs_manual_fetch` evidence get `N/A` score and `Incomplete` in the sufficiency column.
- Scores are a first-pass estimate. A security engineer should validate borderline scores (4-7 range) and any control where recency could not be determined.
