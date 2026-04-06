# ISO 27001:2022 Full Audit - Subagent Runbook

Framework: **ISO 27001:2022**

<!--
  Family list below is duplicated from audits/iso27001/families.json.
  If you add or remove a family, update families.json AND this file.
-->
Families: C.4, C.5, C.6, C.7, C.8, C.9, C.10, A.5, A.6, A.7, A.8

## Per-family prompt

Open your AI agent and run one prompt per family. Each subagent gets its own context
and produces one result file under `audits/iso27001/results/`.

```
Audit the {FAMILY} control family for the iso27001_2022 framework.
Follow the instructions in: prompts/template.md
Replace {FAMILY} with: A.5
Replace {FRAMEWORK} with: iso27001_2022
```

## Suggested sequence

1. C.4, C.5 (Context and Leadership - ISMS scope and commitment)
2. C.6 (Planning - risk assessment and treatment)
3. C.7 (Support - resources, competence, documentation)
4. C.8, C.9, C.10 (Operations, evaluation, and improvement)
5. A.5 (Organizational controls - policies, roles, supplier relations)
6. A.6 (People controls - screening, awareness, remote work)
7. A.7 (Physical controls - perimeters, equipment, cabling)
8. A.8 (Technological controls - access, endpoints, crypto, network, dev)

## Before running

Check for incomplete evidence:

```bash
grep needs_manual_fetch audits/iso27001/mapping.csv
```

Any rows returned = manual retrieval needed before those controls can be scored (they will appear as N/A).

## After running

Results land in `audits/iso27001/results/`:

```
audits/iso27001/results/
  a.5_result.md
  a.6_result.md
  a.7_result.md
  a.8_result.md
  c.4_result.md
  ...
```

Commit results so scores are version-controlled and comparable across audit cycles:

```bash
git add audits/iso27001/results/
git commit -m "audit: iso27001 gap analysis $(date +%Y-%m)"
```

## Interpreting scores

- 8-10: adequately evidenced. Verify recency if dates are missing.
- 4-7: partial gaps. Prioritize remediation based on control criticality.
- 0-3: significant gaps. High priority.
- N/A (needs_manual_fetch): fetch the document, save as `.txt` in `docs/{FAMILY}/`,
  update `mapping.csv` status to `ready`, and re-run the affected family.
