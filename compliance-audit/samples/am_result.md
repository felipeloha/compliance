# AM Gap Analysis - c5

**Audit date:** 2026-05-12
**Evidence reviewed:** `samples/am-policy.md` (v2.1, last reviewed 2024-11-15)
**Auditor note:** A single policy+procedure document covers all AM controls. No operational evidence (inventory exports, commissioning records, decommissioning logs, acknowledgment records) was available locally. All scores are capped at 6/10. A security engineer should validate scores in the 4–6 range and obtain operational evidence before treating any control as fully implemented.

---

| Control | Evidence sources | Content assessed as | Evidence sufficient? | Score (0-10) | Gaps |
|---------|-----------------|---------------------|---------------------|--------------|------|
| AM-01 | am-policy.md §2 | Procedure/Standard | Partial — no operational evidence | 6/10 | No operational evidence — implementation effectiveness unproven. No inventory export, snapshot, or change-log sample available. Note: `doc_type` labeled `documentation` in mapping.csv but content is policy+procedure level. |
| AM-02 | am-policy.md §3, §7 | Procedure/Standard | Partial — gaps and no operational evidence | 5/10 | Remote deactivation/deletion/blocking not addressed. Physical transfer and transport not addressed. Handling of malfunctions and vulnerabilities not explicitly covered. No operational evidence — implementation effectiveness unproven. |
| AM-03 | am-policy.md §4 | Procedure/Standard | Partial — no operational evidence | 6/10 | No operational evidence — implementation effectiveness unproven. No sample commissioning records or approval logs available. |
| AM-04 | am-policy.md §5 | Procedure/Standard | Partial — no operational evidence | 6/10 | No operational evidence — implementation effectiveness unproven. No decommissioning records or media destruction certificates available. |
| AM-05 | am-policy.md §6 | Procedure/Standard | Partial — no operational evidence | 5/10 | Policy does not explicitly reference a risk assessment that gates when this commitment requirement applies (C5 AM-05 requires commitment only where a risk assessment has identified the asset as security-relevant). No sample acknowledgment records or HR system exports available. No operational evidence — implementation effectiveness unproven. |
| AM-06 | am-policy.md §7 | Procedure/Standard | Partial — content gap and no operational evidence | 5/10 | Classification schema covers confidentiality, integrity, and availability but omits **authenticity** as a protection objective, which C5 AM-06 explicitly requires. No operational evidence — implementation effectiveness unproven. No labeled asset samples or system screenshots available. |