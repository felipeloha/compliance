# Vulnerability SLA Reporter

> Blog post: [blog-posts/post-06-vuln-sla-reporter.md](../blog-posts/post-06-vuln-sla-reporter.md)

Fetch vulns from Vanta, compute SLA deadlines, publish to Trust Center, alert on violations.

## Overview

Lambda pipeline for automated vulnerability SLA enforcement:

- Per-severity SLA windows
- Warning vs violation tiers
- Trust Center auto-publish + prune lifecycle

## Configuration

Replace Vanta API endpoint, Slack channel IDs, and Trust Center config with env vars (see `.env.example`).

## Status

TODO: add code.
