# Agent Instructions

## Plan mode

**Always start in plan mode.** Before writing any code, creating any file, or making any change:

1. Read the relevant source files and skills
2. Present a plan using the CreatePlan tool covering: files to extract, sanitization changes, test strategy, and blog post outline
3. Wait for explicit confirmation before proceeding

This is non-negotiable. The plan must be reviewed and approved before execution starts.

---

This repository uses a shared `ai-docs/` directory for project knowledge, feature specs, and reusable skills.

**Always consult `ai-docs/` before starting work.** Relevant docs may already exist for your task.

### Structure

```
ai-docs/
  context/       # Stable project knowledge (product, architecture, conventions, glossary)
  specs/         # Feature and initiative specs (requirements.md, design.md)
  skills/        # Reusable AI-assisted workflows (SKILL.md with YAML frontmatter)
```

### How to use

- **Before implementing a feature**: check `ai-docs/specs/` for existing requirements and design docs
- **Before writing code**: check `ai-docs/skills/` for relevant patterns (endpoints, tests, etc.)
- **For domain or architecture questions**: check `ai-docs/context/`
- **When creating new docs**: follow the `write-ai-docs` skill in `ai-docs/skills/write-ai-docs/SKILL.md`

### Generality rule

This repo is public. All code, READMEs, and blog posts must be generic and reusable by anyone.

Never include or infer:
- Company names, product names, or team names
- Internal service names, cluster names, or environment names
- Organizational structure (team names, org hierarchy, Jira spaces)
- Anything that only makes sense in one specific company's context

When in doubt, abstract it. A reader at a different company should be able to pick up any module or post and apply it directly.

### Skills

Skills are markdown files with YAML frontmatter. The `description` field tells you when to apply them:

| Skill | Trigger |
|-------|---------|
| `write-blog-post` | Writing or drafting any post in `blog-posts/` |
| `sanitize-module` | Adding or reviewing code in any module folder |
| `cdaa-integration-tests` | Running or writing CDAA integration tests |
