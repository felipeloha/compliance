#!/usr/bin/env python3
"""
Bootstrap: pull evidence from a compliance tool and build mapping.csv.

Run once per audit cycle from the compliance-audit directory:

    python -m integrations.vanta.bootstrap --framework iso27001_2022

Or directly (sys.path is patched automatically):

    python integrations/vanta/bootstrap.py --framework iso27001_2022
"""

import argparse
import csv
import dataclasses
import os
import sys
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

from integrations.base import ComplianceIntegration, ControlDocumentationRow, DocumentType  # noqa: E402
from integrations.vanta.vanta_client import VantaAPIClient  # noqa: E402

MAPPING_COLUMNS = ["family", "control", "source_type", "link", "status", "doc_type"]


# ---------------------------------------------------------------------------
# Mapping CSV helpers
# ---------------------------------------------------------------------------


def _parse_doc_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError:
        return DocumentType.NONE


def _load_existing_mapping(mapping_path: Path) -> tuple[list[ControlDocumentationRow], set[tuple]]:
    if not mapping_path.exists():
        return [], set()
    with mapping_path.open(newline="", encoding="utf-8") as f:
        rows = [
            ControlDocumentationRow(
                family=r.get("family", ""),
                control=r.get("control", ""),
                source_type=r.get("source_type", ""),
                link=r.get("link", ""),
                status=r.get("status", ""),
                doc_type=_parse_doc_type(r.get("doc_type", "")),
            )
            for r in csv.DictReader(f)
        ]
    keys = {(r.family, r.control, r.link) for r in rows}
    return rows, keys


def _write_mapping(mapping_path: Path, rows: list[ControlDocumentationRow]) -> None:
    with mapping_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MAPPING_COLUMNS)
        writer.writeheader()
        for row in rows:
            d = dataclasses.asdict(row)
            d["doc_type"] = row.doc_type.value
            writer.writerow(d)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def run_bootstrap(client: ComplianceIntegration, framework: str, docs_dir: Path, mapping_path: Path) -> None:
    print(f"Fetching controls for framework: {framework}")
    controls = client.get_framework_controls(framework)
    print(f"Retrieved {len(controls)} controls")

    existing_rows, existing_keys = _load_existing_mapping(mapping_path)
    new_rows: list[ControlDocumentationRow] = []

    for control in controls:
        for row in client.get_control_documentation(control, docs_dir):
            key = (row.family, row.control, row.link)
            if key not in existing_keys:
                new_rows.append(row)
                existing_keys.add(key)

    all_rows = existing_rows + new_rows
    _write_mapping(mapping_path, all_rows)
    print(f"\nWrote {len(all_rows)} rows to {mapping_path} ({len(new_rows)} new)")

    needs_manual = sum(1 for r in all_rows if r.status == "needs_manual_fetch")
    if needs_manual:
        print(f"Warning: {needs_manual} row(s) with status=needs_manual_fetch - audit will be incomplete")
        print("  Run: grep needs_manual_fetch mapping.csv")


def build_client(tool: str) -> ComplianceIntegration:
    if tool == "vanta":
        client_id = os.environ.get("VANTA_CLIENT_ID", "")
        client_secret = os.environ.get("VANTA_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            print("Error: VANTA_CLIENT_ID and VANTA_CLIENT_SECRET must be set", file=sys.stderr)
            sys.exit(1)
        return VantaAPIClient(client_id, client_secret)
    print(f"Error: unknown compliance tool '{tool}'", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap compliance evidence for audit")
    parser.add_argument(
        "--tool",
        default=os.environ.get("COMPLIANCE_TOOL", "vanta"),
        help="Compliance tool integration to use (default: vanta)",
    )
    parser.add_argument(
        "--framework",
        default=os.environ.get("VANTA_FRAMEWORK_ID", "iso27001_2022"),
        help="Framework ID (default: iso27001_2022)",
    )
    parser.add_argument("--docs-dir", default="docs", help="Directory to write downloaded docs (default: docs)")
    parser.add_argument("--mapping-file", default="mapping.csv", help="Path to mapping.csv (default: mapping.csv)")
    args = parser.parse_args()

    run_bootstrap(
        client=build_client(args.tool),
        framework=args.framework,
        docs_dir=Path(args.docs_dir),
        mapping_path=Path(args.mapping_file),
    )


if __name__ == "__main__":
    main()
