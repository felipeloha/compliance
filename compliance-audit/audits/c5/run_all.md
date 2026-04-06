# C5 Full Audit - Subagent Runbook

Framework: **BSI C5**
<!--
  Family list below is duplicated from audits/c5/families.json.
  If you add or remove a family, update families.json AND this file.
-->
Families: AM, BCM, COM, COS, CRY, DEV, HR, IDM, INQ, OIS, OPS, PI, PS, PSS, SIM, SP, SSO

## Per-family prompt

Open your AI agent and run one prompt per family. Each subagent gets its own context
and produces one result file under `audits/c5/results/`.

```
Audit the {FAMILY} control family for the c5 framework.
Follow the instructions in: prompts/template.md
Replace {FAMILY} with: AM
Replace {FRAMEWORK} with: c5
```

## Suggested sequence

Run families that share evidence independently and in parallel.
SP is referenced in almost every family - audit it first.

1. SP (Security Policies - referenced everywhere)
2. OIS, COM (governance layer)
3. AM, HR, IDM (core operational controls)
4. DEV, OPS, COS, CRY (technical controls)
5. SIM, BCM (incident and continuity)
6. PS, SSO (physical and third-party)
7. INQ, PI, PSS (customer-facing and portability)

## Before running

Check for incomplete evidence:

```bash
grep needs_manual_fetch audits/c5/mapping.csv
```

Any rows returned = manual retrieval needed before those controls can be scored (they will appear as N/A).

## After running

Results land in `audits/c5/results/`:

```
audits/c5/results/
  am_result.md
  hr_result.md
  idm_result.md
  ...
```

Commit results so scores are version-controlled and comparable across audit cycles:

```bash
git add audits/c5/results/
git commit -m "audit: c5 gap analysis $(date +%Y-%m)"
```

## Interpreting scores

- 8-10: adequately evidenced. Verify recency if dates are missing.
- 4-7: partial gaps. Prioritize remediation based on control criticality.
- 0-3: significant gaps. High priority.
- N/A (needs_manual_fetch): fetch the document, save as `.txt` in `docs/{FAMILY}/`,
  update `mapping.csv` status to `ready`, and re-run the affected family.
