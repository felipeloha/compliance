#!/usr/bin/env python3
"""
Export Vanta framework controls to CSV and optionally JSON.

Run from the compliance-audit directory:

    python -m integrations.vanta.collect_controls --framework iso27001_2022
    python -m integrations.vanta.collect_controls --framework iso27001_2022 --include-docs --output-json controls.json
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

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
from integrations.vanta.vanta_client import VantaAPIClient, filter_controls_by_prefixes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Vanta controls to CSV/JSON")
    parser.add_argument(
        "--framework",
        default=os.environ.get("VANTA_FRAMEWORK_ID", "iso27001_2022"),
        help="Framework ID (default: iso27001_2022)",
    )
    parser.add_argument(
        "--prefix",
        nargs="*",
        metavar="PREFIX",
        help="Filter by control name prefix, e.g. --prefix AM IDM",
    )
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Fetch linked document titles and URLs for each control (slower, hits API per control)",
    )
    parser.add_argument(
        "--output-csv",
        default="controls.csv",
        help="Output CSV path (default: controls.csv)",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Also write JSON output to this path",
    )
    args = parser.parse_args()

    client = build_client("vanta")
    app_url = os.environ.get("VANTA_APP_URL", "https://app.vanta.com")

    print(f"Fetching controls for framework: {args.framework}")
    controls = client.get_framework_controls(args.framework)

    if args.prefix:
        controls = filter_controls_by_prefixes(controls, args.prefix)

    print(f"Processing {len(controls)} controls")

    rows: list[dict[str, Any]] = []
    for control in controls:
        family = extract_family(control)
        row: dict[str, Any] = {
            "external_id": control.external_id,
            "name": control.name,
            "family": family,
            "control_url": f"{app_url}/controls/{control.id}",
        }
        if args.include_docs:
            # list_control_documents is only available on VantaAPIClient
            assert isinstance(client, VantaAPIClient)
            docs = client.list_control_documents(control.id)
            row["document_titles"] = "; ".join(d.get("title", "") for d in docs)
            row["document_urls"] = "; ".join(d.get("url", "") for d in docs if d.get("url"))
        rows.append(row)

    if not rows:
        print("No controls found - check --framework and credentials")
        sys.exit(0)

    fieldnames = list(rows[0].keys())
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} controls to {args.output_csv}")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(rows)} controls to {args.output_json}")


if __name__ == "__main__":
    main()
