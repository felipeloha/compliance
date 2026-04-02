# Backup Account Cost Guard

> Blog post: [blog-posts/post-07-backup-cost-guard.md](../blog-posts/post-07-backup-cost-guard.md)

One Lambda, one rule: if anything is running in the backup account at 7am, page the team.

## Overview

Drift detection for backup accounts using an intentional-failure pattern:

- EventBridge cron trigger at 7am
- Lambda checks for unexpected running resources
- CloudWatch alarm chain pages on-call if any resource is found

## Status

TODO: add code.
