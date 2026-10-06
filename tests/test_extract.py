"""Exercise optional extraction without making any external model requests."""

import io
import json
import urllib.error
from pathlib import Path

import pytest

from libs_repro_audit import extract


@pytest.fixture
def configured(monkeypatch):
    values = {
        "LIBS_AUDIT_API_URL": "https://model.example/v1/chat/completions",
        "LIBS_AUDIT_MODEL": "configured-model",
        "LIBS_AUDIT_API_KEY": "unit-test-secret",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


@pytest.fixture
def paper(tmp_path):
    path = tmp_path / "paper.txt"
    path.write_text("C = 5.982; Table 3", encoding="utf-8")
    return path


@pytest.mark.parametrize("missing", extract.CONFIG_VARS)
def test_missing_config_precedes_file_read_and_request(
        configured, missing, monkeypatch, capsys):
    monkeypatch.setenv(missing, "  ")

    def forbidden(*args, **kwargs):
        pytest.fail("missing configuration must not read a file or call an endpoint")

    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(extract.urllib.request, "urlopen", forbidden)
    assert extract.main(["absent.txt"]) == 2
    captured = capsys.readouterr()
    assert missing in captured.err
    assert configured["LIBS_AUDIT_API_KEY"] not in captured.out + captured.err


def test_configured_chat_request_and_unconditional_draft_stamp(
        configured, paper, tmp_path, monkeypatch, capsys):
    result = {"source": "Table 3", "value": 5.982,
              "verification": "verified by model"}
    calls = []

    def mocked_urlopen(request, timeout):
        calls.append(request)
        assert timeout == 180
        assert request.full_url == configured["LIBS_AUDIT_API_URL"]
        assert request.get_method() == "POST"
        assert request.get_header("Authorization") == (
            "Bearer " + configured["LIBS_AUDIT_API_KEY"])
        assert request.get_header("Content-type") == "application/json"
        assert set(dict(request.header_items())) == {"Authorization", "Content-type"}
        payload = json.loads(request.data)
        assert payload["model"] == configured["LIBS_AUDIT_MODEL"]
        assert payload["max_tokens"] == 4000
        assert payload["messages"][0] == {
            "role": "system", "content": extract.EXTRACTION_SYSTEM}
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == (
            "TEMPLATE:\n" + extract._template() +
            "\n\nPAPER TEXT:\n" + paper.read_text())
        return io.BytesIO(json.dumps({"choices": [{
            "message": {"content": json.dumps(result)}}]}).encode())

    monkeypatch.setattr(extract.urllib.request, "urlopen", mocked_urlopen)
    output = tmp_path / "record.json"
    assert extract.main([str(paper), "-o", str(output)]) == 0
    assert len(calls) == 1
    record = json.loads(output.read_text())
    assert record["source"] == "Table 3"
    assert record["value"] == 5.982
    assert record["verification"].startswith("DRAFT — UNVERIFIED:")
    captured = capsys.readouterr()
    assert configured["LIBS_AUDIT_API_KEY"] not in captured.out + captured.err
    assert "verify every value" in captured.out


@pytest.mark.parametrize("fence", ["```json", "```", "```JSON"])
def test_json_fences_are_accepted(configured, paper, tmp_path, monkeypatch, fence):
    monkeypatch.setattr(extract, "_call_api", lambda *args: fence + '\n{"source": "Table 3"}\n```')
    output = tmp_path / "record.json"
    assert extract.main([str(paper), "-o", str(output)]) == 0
    assert json.loads(output.read_text())["verification"].startswith("DRAFT — UNVERIFIED:")


@pytest.mark.parametrize("raw", ["not JSON", "[]", "null", "42", '"text"',
                                '{"value": NaN}', '{"value": 1e400}'])
def test_invalid_output_is_preserved_without_changing_existing_record(
        configured, paper, tmp_path, monkeypatch, raw):
    monkeypatch.setattr(extract, "_call_api", lambda *args: raw)
    output = tmp_path / "record.json"
    output.write_text("previous record", encoding="utf-8")
    assert extract.main([str(paper), "-o", str(output)]) == 1
    assert output.read_text() == "previous record"
    assert Path(str(output) + ".raw.txt").read_text() == raw


def test_invalid_fenced_output_preserves_the_original_response(
        configured, paper, tmp_path, monkeypatch):
    raw = "  ```json\nnot JSON\n```  "
    monkeypatch.setattr(extract, "_call_api", lambda *args: raw)
    output = tmp_path / "record.json"
    assert extract.main([str(paper), "-o", str(output)]) == 1
    assert not output.exists()
    assert Path(str(output) + ".raw.txt").read_text() == raw


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b"{}", b'{"choices": []}',
                                   b'{"choices": [{"message": {"content": null}}]}'])
def test_invalid_endpoint_response_is_preserved_and_not_stamped(
        configured, paper, tmp_path, monkeypatch, body):
    monkeypatch.setattr(extract.urllib.request, "urlopen",
                        lambda *args, **kwargs: io.BytesIO(body))
    output = tmp_path / "record.json"
    assert extract.main([str(paper), "-o", str(output)]) == 1
    assert not output.exists()
    assert Path(str(output) + ".raw.txt").read_bytes() == body


@pytest.mark.parametrize("error_type", [urllib.error.URLError, TimeoutError, ValueError])
def test_request_errors_do_not_expose_credentials(
        configured, paper, tmp_path, monkeypatch, capsys, error_type):
    def failed(*args, **kwargs):
        raise error_type("server echoed " + configured["LIBS_AUDIT_API_KEY"])

    monkeypatch.setattr(extract.urllib.request, "urlopen", failed)
    output = tmp_path / "record.json"
    assert extract.main([str(paper), "-o", str(output)]) == 1
    assert not output.exists()
    captured = capsys.readouterr()
    assert "request failed" in captured.err
    assert configured["LIBS_AUDIT_API_KEY"] not in captured.out + captured.err


def test_help_exposes_required_configuration_without_reading_files(monkeypatch, capsys):
    for name in extract.CONFIG_VARS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit) as exited:
        extract.main(["--help"])
    assert exited.value.code == 0
    help_text = capsys.readouterr().out
    assert all(name in help_text for name in extract.CONFIG_VARS)


def test_missing_paper_reports_a_safe_error(configured, tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("no request should be made when the paper cannot be read")

    monkeypatch.setattr(extract.urllib.request, "urlopen", forbidden)
    assert extract.main([str(tmp_path / "absent.txt")]) == 1
    assert "could not read the paper text file" in capsys.readouterr().err
