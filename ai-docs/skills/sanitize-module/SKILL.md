---
name: sanitize-module
description: Sanitize code in a module folder before publishing. Use when adding, reviewing, or writing any code in module folders in this repo.
---

# Sanitize Module

Before writing or accepting any code into a module folder, check every file for the following. Flag and replace anything found.

## What to detect and replace

| Pattern | Examples | Replace with |
|---------|----------|-------------|
| AWS account IDs | `123456789012` | `${AWS_ACCOUNT_ID}` |
| ARNs with account IDs | `arn:aws:iam::123456789012:role/...` | parameterize account segment |
| AWS access keys | `AKIAIOSFODNN7EXAMPLE` | remove entirely |
| Hardcoded credential values | `password = "s3cr3t"`, `api_key = "abc123"` | `${VAR_NAME}` |
| Internal hostnames or domains | `vault.internal`, `db.corp.example` | `${VAULT_ADDR}`, `${DB_HOST}` |
| Private IP addresses | `10.0.1.5`, `192.168.1.100` | `${SERVICE_HOST}` |
| Slack channel or workspace IDs | `C0123ABCD`, `T01ABCDEF` | `${SLACK_CHANNEL_ID}` |
| Jira project keys | `ENG-123`, `SEC` as a project key | `${JIRA_PROJECT_KEY}` |
| SSO or IdP tenant URLs | `https://sso.acme.com` | `${SSO_URL}` |
| Service account emails | `svc-audit@acme.com` | `${SERVICE_ACCOUNT}` |
| S3 bucket names | `acme-prod-audit-logs` | Terraform variable |
| Repo or internal path references in comments | `# from cloud-setup/terraform/...` | remove the comment |

## What is safe to leave

- `${VAR}` style references
- `example.com`, `your-bucket-name`, `<YOUR_VALUE>` placeholders
- Public AWS service endpoints (`s3.amazonaws.com`, etc.)
- Generic library or framework names

## After replacing

- Add every replaced value to `.env.example` with an empty default or a documented example value.
- Update the module `README.md` Configuration section if it doesn't already reference `.env.example`.
