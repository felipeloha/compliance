# Running the Full Audit with Subagents

For large frameworks with many control families, run one subagent per family in parallel
rather than auditing all families sequentially in a single context window.

## Pattern

Open your AI agent and run the following prompt once per family. Each subagent gets its
own context and produces one result file.

```
Audit the {FAMILY} control family for the {FRAMEWORK} framework.
Follow the instructions in: prompts/template.md
Replace {FAMILY} with: AM
Replace {FRAMEWORK} with: c5
```

Repeat for each family: AM, HR, IDM, BCM, COM, COS, CRY, DEV, INQ, OIS, OPS, PI, PS, PSS, SIM, SP, SSO

## Sequence recommendation

Run families that share evidence independently and in parallel.
Group families that reference each other (e.g., SP-01 is referenced in almost every family)
and audit SP first so subagents can reference the SP score when noting gaps.

Suggested order:
1. SP (referenced everywhere - audit first)
2. OIS, COM (governance layer)
3. AM, HR, IDM (core operational controls)
4. DEV, OPS, COS, CRY (technical controls)
5. SIM, BCM (incident/continuity)
6. PS, SSO (physical and third-party)
7. INQ, PI, PSS (customer-facing and portability)

## Before running

Check audit completeness:

```bash
grep needs_manual_fetch audits/c5/mapping.csv
```

Any rows returned = incomplete evidence for those controls.
Manual retrieval needed before those controls can be scored (they will appear as N/A).

## After running

Results land in `audits/{FRAMEWORK}/results/`:

```
audits/c5/results/
  am_result.md
  hr_result.md
  idm_result.md
  ...
```

Review all result files. Commit them so scores are version-controlled and comparable
across audit cycles:

```bash
git add audits/c5/results/
git commit -m "audit: c5 gap analysis $(date +%Y-%m)"
```

## Interpreting results

- Scores 8-10: adequately evidenced. Verify recency if dates are missing.
- Scores 4-7: partial gaps. Prioritize remediation based on control criticality.
- Scores 0-3: significant gaps. High priority.
- N/A (needs_manual_fetch): fetch the document, save as `.txt` in `docs/{FAMILY}/`,
  update `mapping.csv` status to `ready`, and re-run the affected family.
