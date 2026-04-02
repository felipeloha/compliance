---
name: write-blog-post
description: Write a technical blog post for the compliance repo. Use when drafting or writing any post in blog-posts/.
---

# Write Blog Post

## Voice

- Senior engineer audience. No hand-holding.
- Don't open with "In this post we will...". Start with the challenge or the hook.
- Concrete over abstract. Show the actual moving parts.
- Use "we" only when describing a decision made together, not as a writing device.

## Structure

1. **Hook** - use the hook from the post placeholder. One or two sentences max.
2. **Challenge** - the business or compliance need this solves. What audit, regulation, or operational gap forced this to exist. Short.
3. **Approach** - how the solution is structured at a high level, before diving into implementation. Why this shape and not another. One short paragraph.
4. **Architecture** - how it works. Add a diagram if there are 3+ components or a non-obvious flow.
5. **Code walkthrough** - key snippets only. Explain the non-obvious decisions, not the syntax.
6. **Key decisions** - 2-3 trade-offs worth naming. Why this approach, not the obvious one.
7. **Wrap-up** - 2-3 sentences. What you get out of it. No generic conclusions.

## Diagrams

Add a Mermaid diagram when:
- There are 3+ components interacting
- The request/event flow is not obvious from prose alone

Use `flowchart LR` for pipelines and data flows. Use `sequenceDiagram` for request/response flows. Keep node labels short. Skip diagrams for simple two-step flows.

## Length

Target 800-1200 words. Cut anything that doesn't add signal. A shorter post that covers the key decisions is better than a long one that covers the obvious.
