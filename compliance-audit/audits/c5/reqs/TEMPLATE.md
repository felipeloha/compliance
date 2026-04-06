# FAMILY - Family Name

This file is a template. Copy it to create a new control family req file.

---

## CTRL-01 First control name
Description of the first control requirement. Can span multiple paragraphs.

Plain prose is preferred over bullet points for the main requirement text.
References to other controls are written as plain text (e.g., see CTRL-02).

## CTRL-02 Second control name
Description of the second control. Each `## {ID} {Name}` heading marks a new
control. The `test_mapping.py` integrity test parses these headings to build
the list of valid control IDs for a family.

## CTRL-03 Third control name
Add as many controls as needed. One heading per control. No nesting.
