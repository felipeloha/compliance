import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.vanta.bootstrap import run_bootstrap
from integrations.vanta.vanta_client import VantaAPIClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_response(status_code: int, json_data=None, content: bytes | None = None) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.text = ""
    if json_data is not None:
        m.json.return_value = json_data
    if content is not None:
        m.content = content
    return m


def token_ok() -> MagicMock:
    return make_response(200, {"access_token": "tok", "expires_in": 3600})


def one_page(data: list) -> MagicMock:
    return make_response(200, {"results": {"data": data, "pageInfo": {"hasNextPage": False}}})


def file_ok(content: bytes) -> MagicMock:
    return make_response(200, content=content)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> VantaAPIClient:
    return VantaAPIClient("test-id", "test-secret")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBootstrapE2E:
    def test_plain_file_upload_writes_ready_row(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Security Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "security-policy.txt"}]),
                file_ok(b"policy content"),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        txt = docs_dir / "AM" / "security-policy.txt"
        assert txt.exists()
        assert txt.read_bytes() == b"policy content"

        rows = read_csv(mapping)
        assert len(rows) == 1
        assert rows[0]["family"] == "AM"
        assert rows[0]["control"] == "AM-01"
        assert rows[0]["source_type"] == "local_file"
        assert rows[0]["status"] == "ready"
        assert "security-policy.txt" in rows[0]["link"]

    def test_pdf_upload_extracts_text(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        with (
            patch("time.sleep"),
            patch("requests.post", return_value=token_ok()),
            patch("requests.get") as mock_get,
            patch("integrations.utils.pdf_bytes_to_text", return_value="extracted text"),
        ):
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.pdf"}]),
                file_ok(b"%PDF-1.4 fake"),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        txt = docs_dir / "AM" / "policy.txt"
        assert txt.exists()
        assert txt.read_text() == "extracted text"

        rows = read_csv(mapping)
        assert rows[0]["status"] == "ready"

    def test_pdf_conversion_failure_falls_back_to_raw_content(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"
        raw = b"%PDF-1.4 raw content"

        with (
            patch("time.sleep"),
            patch("requests.post", return_value=token_ok()),
            patch("requests.get") as mock_get,
            patch("integrations.utils.pdf_bytes_to_text", return_value=None),
        ):
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.pdf"}]),
                file_ok(raw),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        txt = docs_dir / "AM" / "policy.txt"
        assert txt.exists()
        assert txt.read_bytes() == raw

        rows = read_csv(mapping)
        assert rows[0]["status"] == "ready"

    def test_word_doc_upload_writes_placeholder(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.docx"}]),
                file_ok(b"PK\x03\x04fake docx bytes"),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        txt = docs_dir / "AM" / "policy.txt"
        assert txt.exists()
        assert "[Word document:" in txt.read_text()

        rows = read_csv(mapping)
        assert rows[0]["status"] == "ready"

    def test_confluence_url_writes_needs_manual_fetch(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"
        url = "https://yourorg.atlassian.net/wiki/spaces/SEC/pages/12345"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "IDM-01", "name": "IDM-01 Access"}]),
                one_page([{"id": "doc1", "title": "Access Policy", "url": url}]),
                one_page([]),  # no uploads
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        rows = read_csv(mapping)
        assert len(rows) == 1
        assert rows[0]["family"] == "IDM"
        assert rows[0]["source_type"] == "confluence"
        assert rows[0]["link"] == url
        assert rows[0]["status"] == "needs_manual_fetch"

    def test_external_url_writes_needs_manual_fetch(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"
        url = "https://vendor.example.com/sla-doc.pdf"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "BCM-01", "name": "BCM-01 Continuity"}]),
                one_page([{"id": "doc1", "title": "SLA Doc", "url": url}]),
                one_page([]),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        rows = read_csv(mapping)
        assert rows[0]["source_type"] == "external_url"
        assert rows[0]["status"] == "needs_manual_fetch"

    def test_second_run_does_not_duplicate_rows(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        # second run fetches controls/docs/uploads but skips the download (row_key already in mapping)
        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.txt"}]),
                file_ok(b"content"),
                # second run
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.txt"}]),
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        rows = read_csv(mapping)
        assert len(rows) == 1

    def test_same_doc_linked_to_two_controls_downloaded_once(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([
                    {"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"},
                    {"id": "ctrl2", "externalId": "AM-02", "name": "AM-02 Acceptable use"},
                ]),
                one_page([{"id": "doc1", "title": "Shared Policy", "url": ""}]),  # ctrl1 docs
                one_page([{"id": "up1", "fileName": "shared-policy.txt"}]),        # doc1 uploads
                file_ok(b"shared content"),                                          # download
                one_page([{"id": "doc1", "title": "Shared Policy", "url": ""}]),  # ctrl2 docs (same doc)
                one_page([{"id": "up1", "fileName": "shared-policy.txt"}]),        # doc1 uploads again
                # no download - already in downloaded_docs
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        rows = read_csv(mapping)
        assert len(rows) == 2
        assert {r["control"] for r in rows} == {"AM-01", "AM-02"}
        assert mock_get.call_count == 6  # not 7 - download called once

    def test_download_failure_skips_row_without_crash(self, tmp_path, client):
        docs_dir = tmp_path / "docs"
        mapping = tmp_path / "mapping.csv"

        with patch("time.sleep"), patch("requests.post", return_value=token_ok()), patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "ctrl1", "externalId": "AM-01", "name": "AM-01 Inventory"}]),
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.txt"}]),
                make_response(403),  # download fails
            ]
            run_bootstrap(client, "iso27001_2022", docs_dir, mapping)

        rows = read_csv(mapping)
        assert len(rows) == 0
        assert not (docs_dir / "AM" / "policy.txt").exists()
