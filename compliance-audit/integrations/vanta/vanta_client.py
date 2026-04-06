"""Vanta API client: OAuth client credentials, rate limiting, cursor pagination."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from integrations.base import ComplianceIntegration, Control, ControlDocumentationRow
from integrations.utils import extract_family, safe_filename, save_file_as_txt, source_type_from_url

# ---------------------------------------------------------------------------
# Vanta-internal data types (not part of the shared contract)
# ---------------------------------------------------------------------------


@dataclass
class _Document:
    id: str
    title: str
    url: str


@dataclass
class _Upload:
    id: str
    file_name: str


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class VantaAPIClient(ComplianceIntegration):
    """Client for the Vanta API using OAuth client credentials flow.

    Rate limit: 50 requests/minute for management endpoints.
    """

    BASE_URL = "https://api.vanta.com"
    TOKEN_URL = "https://api.vanta.com/oauth/token"
    REQUESTS_PER_MINUTE = 50

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._min_request_interval = 60.0 / self.REQUESTS_PER_MINUTE
        self._last_request_time: float = 0
        # Cache: doc_id -> upload_id -> saved txt path (avoids re-downloading
        # the same file when it is linked to multiple controls in one run)
        self._downloaded: dict[str, dict[str, Path]] = {}

    def _enforce_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get_access_token(self) -> str | None:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "vanta-api.all:read",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            response = requests.post(self.TOKEN_URL, data=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            print(f"Token request error: {exc}")
            return None

        if response.status_code != 200:
            print(f"Token request failed: {response.status_code} {response.text}")
            return None

        token_data = response.json()
        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        # Refresh 60s before actual expiry to avoid using a token right as it expires
        self._token_expires_at = time.time() + expires_in - 60
        return self._access_token

    def make_api_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._enforce_rate_limit()

        token = self.get_access_token()
        if not token:
            return {"error": "Failed to get access token"}

        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers, params=params or {}, timeout=30)
        except requests.RequestException as exc:
            return {"error": str(exc)}

        if response.status_code != 200:
            print(f"API request failed: {response.status_code} for {endpoint}")
            return {"error": f"API request failed: {response.status_code}"}

        return response.json()

    def _paginate(self, endpoint: str) -> list[dict[str, Any]]:
        """Collect all pages for a cursor-paginated endpoint. Returns raw dicts."""
        results: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"pageSize": 100}
            if cursor:
                params["pageCursor"] = cursor

            data = self.make_api_request(endpoint, params)
            if "error" in data:
                break

            page_results = data.get("results", {})
            results.extend(page_results.get("data", []))

            page_info = page_results.get("pageInfo", {})
            if not page_info.get("hasNextPage", False):
                break
            cursor = page_info.get("endCursor")

        return results

    def get_framework_controls(self, framework_id: str) -> list[Control]:
        return [
            Control(id=d.get("id", ""), external_id=d.get("externalId", ""), name=d.get("name", ""))
            for d in self._paginate(f"/v1/frameworks/{framework_id}/controls")
        ]

    def list_control_documents(self, control_id: str) -> list[dict[str, Any]]:
        """Return raw document metadata for a control without downloading files."""
        return self._paginate(f"/v1/controls/{control_id}/documents")

    def get_control_documentation(self, control: Control, docs_dir: Path) -> list[ControlDocumentationRow]:
        """Fetch all Vanta documents for a control and materialise them locally.

        For each document:
        - If it has uploaded files: download each file and save as .txt under
          ``docs_dir/<family>/``, returning a ``local_file`` row.
        - If it has only a URL: return a ``needs_manual_fetch`` row with the
          link preserved.
        """
        family = extract_family(control)
        print(f"Processing {control.external_id or control.id}")
        rows: list[ControlDocumentationRow] = []

        for raw_doc in self._paginate(f"/v1/controls/{control.id}/documents"):
            doc = _Document(
                id=raw_doc.get("id", ""),
                title=raw_doc.get("title", ""),
                url=raw_doc.get("url", ""),
            )
            rows.extend(self._materialise_document(doc, control, family, docs_dir))

        return rows

    def _materialise_document(
        self,
        doc: _Document,
        control: Control,
        family: str,
        docs_dir: Path,
    ) -> list[ControlDocumentationRow]:
        uploads = [
            _Upload(id=d.get("id", ""), file_name=d.get("fileName", d.get("name", "")))
            for d in self._paginate(f"/v1/documents/{doc.id}/uploads")
        ]

        if uploads:
            family_dir = docs_dir / family
            family_dir.mkdir(parents=True, exist_ok=True)
            rows = []
            for upload in uploads:
                row = self._materialise_upload(upload, doc, control, family, family_dir)
                if row:
                    rows.append(row)
            return rows

        if doc.url:
            return [
                ControlDocumentationRow(
                    family=family,
                    control=control.external_id,
                    source_type=source_type_from_url(doc.url),
                    link=doc.url,
                    status="needs_manual_fetch",
                )
            ]

        return []

    def _materialise_upload(
        self,
        upload: _Upload,
        doc: _Document,
        control: Control,
        family: str,
        family_dir: Path,
    ) -> ControlDocumentationRow | None:
        base_name = safe_filename(Path(upload.file_name).stem)
        txt_path = family_dir / f"{base_name}.txt"

        if doc.id in self._downloaded and upload.id in self._downloaded[doc.id]:
            txt_path = self._downloaded[doc.id][upload.id]
        elif txt_path.exists():
            self._downloaded.setdefault(doc.id, {})[upload.id] = txt_path
        else:
            content = self._download_file(doc.id, upload.id)
            if content is None:
                print(f"  Could not download {upload.file_name} for {control.external_id}")
                return None
            txt_path = save_file_as_txt(content, upload.file_name, family_dir, base_name)
            self._downloaded.setdefault(doc.id, {})[upload.id] = txt_path
            print(f"  Saved {txt_path}")

        return ControlDocumentationRow(
            family=family,
            control=control.external_id,
            source_type="local_file",
            link=str(txt_path),
            status="ready",
        )

    def _download_file(self, document_id: str, uploaded_file_id: str) -> bytes | None:
        self._enforce_rate_limit()

        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.BASE_URL}/v1/documents/{document_id}/uploads/{uploaded_file_id}/file"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, timeout=60)
        except requests.RequestException as exc:
            print(f"Download error: {exc}")
            return None

        if response.status_code != 200:
            print(f"Download failed: {response.status_code} for {document_id}/{uploaded_file_id}")
            return None

        return response.content


def filter_controls_by_prefixes(controls: list[Control], prefixes: list[str]) -> list[Control]:
    """Filter controls by name prefix. Empty list returns all controls unchanged."""
    if not prefixes:
        return controls
    return [c for c in controls if any(c.name.startswith(p) for p in prefixes)]
