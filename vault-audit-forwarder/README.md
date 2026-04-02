# Vault Audit Forwarder

> Blog post: [blog-posts/post-05-vault-audit-forwarder.md](../blog-posts/post-05-vault-audit-forwarder.md)

Dynamic DB credentials give you security. Vault audit log parsing gives you accountability.

## Overview

Correlates `VaultCredsIssued` to `DbSessionConnect` by username, multi-strategy email resolution (OIDC prefix stripping, SSO principalId, IAM user tags), and forwards to CloudTrail Lake.

## Status

TODO: add code.
