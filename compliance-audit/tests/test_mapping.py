"""Integrity tests for all audits/{framework}/mapping.csv files.

Checks:
- All required columns are non-empty on every row.
- status is one of the allowed enum values.
- status=ready + source_type=local_file rows have an existing local file.
- control column (when filled) matches a known control ID from the corresponding .req file.
"""

import csv
import re
from pathlib import Path

# compliance-audit/ root (two levels up from this file)
MODULE_ROOT = Path(__file__).resolve().parent.parent
AUDITS_DIR = MODULE_ROOT / "audits"

REQUIRED_COLUMNS = ("family", "source_type", "link", "status")
ALLOWED_STATUSES = {"ready", "needs_manual_fetch"}
CONTROL_ID_PATTERN = re.compile(r"^## ([A-Z]+-\d+) ")


def _parse_control_ids(req_file: Path) -> set[str]:
    """Extract ## {ID} headings from a .md req file."""
    ids: set[str] = set()
    for line in req_file.read_text(encoding="utf-8").splitlines():
        match = CONTROL_ID_PATTERN.match(line)
        if match:
            ids.add(match.group(1))
    return ids


def _valid_ids_for_framework(framework_dir: Path) -> dict[str, set[str]]:
    """Return {family_upper: {control_ids}} for all .md req files in the framework."""
    result: dict[str, set[str]] = {}
    reqs_dir = framework_dir / "reqs"
    if not reqs_dir.exists():
        return result
    for req_file in reqs_dir.glob("*.md"):
        if req_file.name.upper() == "TEMPLATE.MD":
            continue
        family = req_file.stem.upper()
        result[family] = _parse_control_ids(req_file)
    return result


def _framework_dirs() -> list[Path]:
    if not AUDITS_DIR.exists():
        return []
    return [d for d in AUDITS_DIR.iterdir() if d.is_dir()]


def test_mapping_required_columns_non_empty() -> None:
    """Every row in every mapping.csv has non-empty values for required columns."""
    for framework_dir in _framework_dirs():
        mapping_file = framework_dir / "mapping.csv"
        if not mapping_file.exists():
            continue
        with mapping_file.open(newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                for col in REQUIRED_COLUMNS:
                    assert row.get(col), (
                        f"{mapping_file}:{i} - column '{col}' is empty: {dict(row)}"
                    )


def test_mapping_valid_status() -> None:
    """Every row has a status from the allowed set."""
    for framework_dir in _framework_dirs():
        mapping_file = framework_dir / "mapping.csv"
        if not mapping_file.exists():
            continue
        with mapping_file.open(newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                status = row.get("status", "")
                assert status in ALLOWED_STATUSES, (
                    f"{mapping_file}:{i} - invalid status '{status}', "
                    f"expected one of {ALLOWED_STATUSES}"
                )


def test_mapping_ready_files_exist() -> None:
    """status=ready + source_type=local_file rows point to existing files."""
    for framework_dir in _framework_dirs():
        mapping_file = framework_dir / "mapping.csv"
        if not mapping_file.exists():
            continue
        with mapping_file.open(newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                if row.get("status") == "ready" and row.get("source_type") == "local_file":
                    file_path = MODULE_ROOT / row["link"]
                    assert file_path.exists(), (
                        f"{mapping_file}:{i} - file not found: {file_path} "
                        f"(link='{row['link']}')"
                    )


def test_mapping_control_ids_valid() -> None:
    """control column (when filled) must match a known ID from the req file."""
    for framework_dir in _framework_dirs():
        mapping_file = framework_dir / "mapping.csv"
        if not mapping_file.exists():
            continue
        valid_ids = _valid_ids_for_framework(framework_dir)
        with mapping_file.open(newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                control = row.get("control", "").strip()
                if not control:
                    continue
                family = row.get("family", "").strip().upper()
                if family not in valid_ids:
                    # No req file for this family - skip ID validation
                    continue
                assert control in valid_ids[family], (
                    f"{mapping_file}:{i} - unknown control ID '{control}' "
                    f"for family '{family}'. Known IDs: {sorted(valid_ids[family])}"
                )
