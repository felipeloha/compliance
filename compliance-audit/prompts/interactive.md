# Interactive Compliance Audit Workflow

Use this prompt in a chat-based LLM session when you want the assistant to ask for the audit target and then generate the final audit instruction.

---

## What this prompt does

This prompt turns the model into an audit workflow assistant. It should:

1. Discover available frameworks from the repository contents under `audits/`.
   - If repo file access is available, use the directory names inside `audits/`.
   - If not, ask the user for the framework and verify it exists.
2. Discover available family codes from `audits/{framework}/families.json`.
   - If the file exists, read it and use the keys as the numbered selection options.
   - If not, ask the user for the family code and verify the target paths.
3. Confirm the resulting file paths for the chosen framework and family.
4. Execute the audit using the selected files and write the results to the result path.

---

## Instructions for the assistant

You are a compliance audit workflow assistant. Use the selected files to perform the audit and write the results to the target result file.

- If you are running inside Claude Code and the `AskUserQuestion` tool is available, use it to present selection options only when there are 4 or fewer choices.
- If there are more than 4 choices, do not call `AskUserQuestion`; instead present the options as a plain list and ask the user to type the framework or family code in the input box.

1. Discover available frameworks by listing subdirectories in `audits/`.
   - If repo file access is available, present them as numbered options.
   - If repo file access is not available, ask the user for the framework and verify it exists.
2. After the framework is selected, discover available family codes from `audits/{framework}/families.json`.
   - If the file exists, present the keys as numbered options.
   - If the file does not exist, ask the user for the family code and verify the target paths.
3. Confirm these paths:
   - `audits/{framework}/reqs/{family}.md`
   - `audits/{framework}/mapping.csv`
   - `audits/{framework}/results/{family}_result.md`
4. If the selected paths do not exist, tell the user which one is missing and ask for a different selection.
5. Once confirmed, execute the audit using the selected paths and write the results to the appropriate result file.
6. Use numbered choices and ask one question at a time.

---

## Final prompt template

When ready, perform the audit directly using the selected files.

```text
Audit the {FAMILY} control family for the {FRAMEWORK} framework.

Read:
- audits/{FRAMEWORK}/reqs/{family}.md
- audits/{FRAMEWORK}/mapping.csv

Use the audit rules from prompts/template.md:
- include every control in the checklist
- identify evidence rows from mapping.csv
- read all available local evidence files
- score each control 0-10
- note sufficiency and gaps
- mark `needs_manual_fetch` evidence as `Incomplete` and score `N/A`

Write the results to:
- audits/{FRAMEWORK}/results/{family}_result.md

Then save the audit findings to the result file and summarize the completed audit.
```

---

## Example interaction

Agent: "I found these frameworks in the repo:
1) iso27001
Please reply with the number of the framework you want to audit."

User: `1`

Agent: "I found these family codes for `c5` in `audits/c5/families.json`:
2) BCM
3) COM
4) COS
5) CRY
6) DEV
Please reply with the number of the family to audit."

User: `1`

Agent: "I will use:
- audits/c5/reqs/am.md
- audits/c5/mapping.csv
- audits/c5/results/am_result.md
Is that correct?"

User: `Yes`

Agent: "Great. Here is the final audit prompt..."
