# compliance

A collection of engineering patterns for building compliance tooling without buying more SaaS. Aligns with C5 and ISO 27001 requirements.

Each module is self-contained and paired with a blog post explaining the design decisions.

## Modules

| Folder | What it does |
|---|---|
| [cdaa/](cdaa/) | Customer data access audit: Slack request -> DynamoDB -> CloudTrail Lake -> Jira violations |
| [vault-audit-forwarder/](vault-audit-forwarder/) | Correlates Vault dynamic credentials to DB sessions and forwards to CloudTrail Lake |
| [dev-access-scripts/](dev-access-scripts/) | One-command access chain: AWS SSO -> SSM tunnel -> Vault OIDC -> short-lived DB credentials |
| [ci-templates/](ci-templates/) | GitLab CI jobs: C5 compliance gate + content-fingerprint-based cache skip |
| [vuln-sla-reporter/](vuln-sla-reporter/) | Fetches vulns from Vanta, enforces SLA windows, publishes to Trust Center, alerts on violations |
| [backup-cost-guard/](backup-cost-guard/) | Detects unexpected resources in the backup account via intentional-failure Lambda pattern |
| [compliance-audit/](compliance-audit/) | AI-assisted compliance gap analysis: prompt pipeline + Vanta MCP + per-domain scoring |

## Blog Posts

All posts live in [blog-posts/](blog-posts/), grouped by series:

**Series 1 - Compliance without the theater**

- [Post 1: C5 compliance gate in CI](blog-posts/post-01-c5-compliance-gate.md)
- [Post 2: AI-powered compliance audit pipeline](blog-posts/post-02-ai-compliance-audit.md)
- [Post 3: CDAA - proving every production data access was justified](blog-posts/post-03-cdaa.md)

**Series 2 - Zero-trust that developers actually use**

- [Post 4: The full access chain](blog-posts/post-04-dev-access-scripts.md)
- [Post 5: Recovering the human behind a DB session](blog-posts/post-05-vault-audit-forwarder.md)

**Series 3 - Practical ops automation**

- [Post 6: Vulnerability SLA enforcement](blog-posts/post-06-vuln-sla-reporter.md)
- [Post 7: The backup account cost guard](blog-posts/post-07-backup-cost-guard.md)
- [Post 8: Skip CI jobs with content fingerprinting](blog-posts/post-08-skip-if-passed.md)
