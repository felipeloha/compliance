import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from integrations.base import Control
from integrations.vanta.vanta_client import VantaAPIClient, filter_controls_by_prefixes

TOKEN_RESPONSE = {
    "access_token": "test-token-abc",
    "expires_in": 3600,
    "token_type": "Bearer",
}


def mock_response(status_code: int, json_data=None, content: bytes | None = None) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.text = str(json_data)
    if json_data is not None:
        m.json.return_value = json_data
    if content is not None:
        m.content = content
    return m


# ---------------------------------------------------------------------------
# Token lifecycle
# ---------------------------------------------------------------------------


class TestTokenLifecycle:
    def test_fetch_success(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response(200, TOKEN_RESPONSE)
            client = VantaAPIClient("client-id", "client-secret")
            token = client.get_access_token()

        assert token == "test-token-abc"
        mock_post.assert_called_once()

    def test_cache_hit(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response(200, TOKEN_RESPONSE)
            client = VantaAPIClient("client-id", "client-secret")
            client.get_access_token()
            token = client.get_access_token()

        assert token == "test-token-abc"
        assert mock_post.call_count == 1

    def test_expired_token_refreshes(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response(200, TOKEN_RESPONSE)
            client = VantaAPIClient("client-id", "client-secret")
            client.get_access_token()
            client._token_expires_at = time.time() - 1  # force expiry
            client.get_access_token()

        assert mock_post.call_count == 2

    def test_http_error_returns_none(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response(401, {"error": "unauthorized"})
            client = VantaAPIClient("client-id", "client-secret")
            token = client.get_access_token()

        assert token is None


# ---------------------------------------------------------------------------
# make_api_request
# ---------------------------------------------------------------------------


class TestMakeApiRequest:
    def _authed_client(self) -> VantaAPIClient:
        client = VantaAPIClient("id", "secret")
        client._access_token = "tok"
        client._token_expires_at = time.time() + 3600
        return client

    def test_success_returns_json(self):
        client = self._authed_client()
        payload = {"results": {"data": [{"id": "c1"}], "pageInfo": {"hasNextPage": False}}}

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response(200, payload)
            result = client.make_api_request("/v1/frameworks/iso27001_2022/controls")

        assert result == payload

    def test_non_200_returns_error_dict(self):
        client = self._authed_client()

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response(404, {"message": "Not Found"})
            result = client.make_api_request("/v1/frameworks/missing/controls")

        assert "error" in result


# ---------------------------------------------------------------------------
# get_framework_controls (pagination)
# ---------------------------------------------------------------------------


class TestGetFrameworkControls:
    def test_two_page_pagination(self):
        client = VantaAPIClient("id", "secret")
        client._access_token = "tok"
        client._token_expires_at = time.time() + 3600

        page1 = {
            "results": {
                "data": [{"id": "c1", "name": "AM-01 Asset inventory"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
            }
        }
        page2 = {
            "results": {
                "data": [{"id": "c2", "name": "AM-02 Acceptable use"}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [mock_response(200, page1), mock_response(200, page2)]
            controls = client.get_framework_controls("iso27001_2022")

        assert len(controls) == 2
        assert controls[0].id == "c1"
        assert controls[1].id == "c2"
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# get_control_documentation
# ---------------------------------------------------------------------------


def one_page(data: list) -> MagicMock:
    return mock_response(200, {"results": {"data": data, "pageInfo": {"hasNextPage": False}}})


class TestGetControlDocumentation:
    def _authed_client(self) -> VantaAPIClient:
        client = VantaAPIClient("id", "secret")
        client._access_token = "tok"
        client._token_expires_at = time.time() + 3600
        return client

    def test_uploaded_file_returns_local_file_row(self, tmp_path: Path):
        client = self._authed_client()
        control = Control(id="ctrl1", external_id="AM-01", name="AM-01 Inventory")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "doc1", "title": "Policy", "url": ""}]),
                one_page([{"id": "up1", "fileName": "policy.txt"}]),
                mock_response(200, content=b"content"),
            ]
            rows = client.get_control_documentation(control, tmp_path)

        assert len(rows) == 1
        assert rows[0].source_type == "local_file"
        assert rows[0].status == "ready"
        assert rows[0].family == "AM"
        assert rows[0].control == "AM-01"
        assert (tmp_path / "AM" / "policy.txt").exists()

    def test_url_only_doc_returns_needs_manual_fetch(self, tmp_path: Path):
        client = self._authed_client()
        control = Control(id="ctrl1", external_id="IDM-01", name="IDM-01 Access")
        url = "https://example.atlassian.net/wiki/spaces/SEC/pages/1"

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "doc1", "title": "Access Policy", "url": url}]),
                one_page([]),  # no uploads
            ]
            rows = client.get_control_documentation(control, tmp_path)

        assert len(rows) == 1
        assert rows[0].source_type == "confluence"
        assert rows[0].status == "needs_manual_fetch"
        assert rows[0].link == url

    def test_same_upload_cached_across_controls(self, tmp_path: Path):
        client = self._authed_client()
        ctrl1 = Control(id="c1", external_id="AM-01", name="AM-01 Inventory")
        ctrl2 = Control(id="c2", external_id="AM-02", name="AM-02 Acceptable use")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                one_page([{"id": "doc1", "title": "Shared", "url": ""}]),
                one_page([{"id": "up1", "fileName": "shared.txt"}]),
                mock_response(200, content=b"shared content"),
                one_page([{"id": "doc1", "title": "Shared", "url": ""}]),
                one_page([{"id": "up1", "fileName": "shared.txt"}]),
                # no download - cache hit
            ]
            rows1 = client.get_control_documentation(ctrl1, tmp_path)
            rows2 = client.get_control_documentation(ctrl2, tmp_path)

        assert mock_get.call_count == 5  # not 6 - download called once
        assert len(rows1) == 1
        assert len(rows2) == 1


# ---------------------------------------------------------------------------
# filter_controls_by_prefixes
# ---------------------------------------------------------------------------


class TestFilterControlsByPrefixes:
    CONTROLS = [
        Control(id="c1", external_id="AM-01", name="AM-01 Inventory of assets"),
        Control(id="c2", external_id="AM-02", name="AM-02 Acceptable use"),
        Control(id="c3", external_id="IDM-01", name="IDM-01 Access control"),
        Control(id="c4", external_id="BCM-01", name="BCM-01 Business continuity"),
    ]

    def test_single_prefix(self):
        result = filter_controls_by_prefixes(self.CONTROLS, ["AM"])
        assert len(result) == 2
        assert all(c.name.startswith("AM") for c in result)

    def test_multiple_prefixes(self):
        result = filter_controls_by_prefixes(self.CONTROLS, ["AM", "BCM"])
        assert len(result) == 3

    def test_empty_list_returns_all(self):
        result = filter_controls_by_prefixes(self.CONTROLS, [])
        assert result == self.CONTROLS

    def test_no_match_returns_empty(self):
        result = filter_controls_by_prefixes(self.CONTROLS, ["XYZ"])
        assert result == []
