# Developer Access Scripts

> Blog post: [blog-posts/post-04-dev-access-scripts.md](../blog-posts/post-04-dev-access-scripts.md)

One command: AWS SSO -> SSM tunnel -> Vault OIDC -> short-lived DB credentials on your clipboard.

## Overview

Three scripts forming a complete zero-trust access chain for developers:

- `pydasso` - AWS SSO login with stdout/eval pattern and token cache fast-path
- `start-ssm-tunnel` - Self-healing SSM tunnel
- `get-vault-db-credentials` - Auto-clipboard short-lived DB credentials via Vault OIDC

## Configuration

Copy `.env.example` to `.env` and fill in your values before use.

## Status

TODO: add code.
