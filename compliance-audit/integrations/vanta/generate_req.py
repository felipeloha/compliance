#!/usr/bin/env python3
"""
Generate .md requirement skeleton files from Vanta framework controls.

Calls GET /v1/frameworks/{id}/controls and writes one .md file per control family
under the specified output directory. Each control gets a ## heading with its ID
and name, and a placeholder for the requirement text.

Run from the compliance-audit directory:

    python -m integrations.vanta.generate_req --framework iso27001_2022 --output-dir audits/iso27001/reqs
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

# Make project root importable when running as a script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from integrations.utils import extract_family  # noqa: E402
from integrations.vanta.bootstrap import build_client  # noqa: E402

FAMILY_NAMES: dict[str, str] = {
    "AM": "Asset Management",
    "BCM": "Business Continuity Management",
    "COM": "Compliance",
    "COS": "Communication Security",
    "CRY": "Cryptography",
    "DEV": "Secure Development",
    "HR": "Human Resources",
    "IDM": "Identity and Access Management",
    "INQ": "Investigation Requests",
    "OIS": "Organizational Information Security",
    "OPS": "Operations Security",
    "PI": "Portability and Interoperability",
    "PS": "Physical Security",
    "PSS": "Product and Service Security",
    "SIM": "Security Incident Management",
    "SP": "Security Policies",
    "SSO": "Supplier and Service Provider Management",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate .md req skeleton files from Vanta framework controls"
    )
    parser.add_argument(
        "--framework",
        default=os.environ.get("VANTA_FRAMEWORK_ID", "iso27001_2022"),
        help="Framework ID (default: iso27001_2022)",
    )
    parser.add_argument(
        "--output-dir",
        default="reqs",
        help="Directory to write .md files (default: reqs)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .md files (default: skip existing)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = build_client("vanta")

    print(f"Fetching controls for framework: {args.framework}")
    controls = client.get_framework_controls(args.framework)
    print(f"Retrieved {len(controls)} controls")

    # Group controls by family
    by_family: dict[str, list] = defaultdict(list)
    for control in controls:
        family = extract_family(control)
        by_family[family].append(control)

    written = 0
    skipped = 0

    for family, family_controls in sorted(by_family.items()):
        out_path = output_dir / f"{family.lower()}.md"

        if out_path.exists() and not args.overwrite:
            print(f"  Skipping {out_path} (already exists, use --overwrite to replace)")
            skipped += 1
            continue

        family_name = FAMILY_NAMES.get(family, family)
        lines = [f"# {family} - {family_name}", ""]

        # Sort controls by external_id, falling back to name
        sorted_controls = sorted(family_controls, key=lambda c: c.external_id or c.name)

        for control in sorted_controls:
            ctrl_id = control.external_id or ""
            ctrl_name = control.name.removeprefix(ctrl_id).strip() if ctrl_id else control.name
            lines.append(f"## {ctrl_id} {ctrl_name}".strip())
            lines.append("[FILL IN REQUIREMENT TEXT]")
            lines.append("")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  Wrote {out_path} ({len(sorted_controls)} controls)")
        written += 1

    print(f"\nDone: {written} files written, {skipped} skipped")
    if written > 0:
        print("Edit the [FILL IN REQUIREMENT TEXT] placeholders before using for audit.")


if __name__ == "__main__":
    main()
