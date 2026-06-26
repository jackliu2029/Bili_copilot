"""Tests for bili_copilot.cli."""

import pytest
from pathlib import Path

from bili_copilot.cli import main
from bili_copilot.pipeline import PipelineError


_FAKE_COOKIE_VALUE = "fake_session_value_12345"
_FAKE_COOKIE_HEADER = f"SESSDATA={_FAKE_COOKIE_VALUE}; bili_jct=fake_csrf_value"


def test_cli_success_returns_zero(monkeypatch, tmp_path):
    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["https://www.bilibili.com/video/BV1xx411c7mD"])
    assert code == 0


def test_cli_success_prints_output_dir(capsys, monkeypatch, tmp_path):
    expected_dir = tmp_path / "output_dir"

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        return expected_dir

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    main(["BV1xx411c7mD"])
    captured = capsys.readouterr()

    assert str(expected_dir) in captured.out


def test_cli_pipeline_error_returns_non_zero(monkeypatch):
    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        raise PipelineError("Invalid input")

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["not-a-link"])
    assert code != 0


def test_cli_output_argument_passed_to_pipeline(monkeypatch, tmp_path):
    captured = {}

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        captured["output_base"] = output_base
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    main(["BV1xx411c7mD", "--output", "custom_outputs"])

    assert captured["output_base"] == Path("custom_outputs")


def test_cli_does_not_make_network_requests(monkeypatch):
    calls = []

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        calls.append(input_url)
        return Path("/fake/output")

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    main(["BV1xx411c7mD"])

    assert calls == ["BV1xx411c7mD"]


def test_cli_cookie_file_passes_header_to_pipeline(monkeypatch, tmp_path):
    cookie_file = tmp_path / "bili_cookie.txt"
    cookie_file.write_text(
        f"SESSDATA={_FAKE_COOKIE_VALUE}\nbili_jct=fake_csrf_value\n",
        encoding="utf-8",
    )
    captured = {}

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        captured["cookie_header"] = cookie_header
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["BV1xx411c7mD", "--cookie-file", str(cookie_file)])
    assert code == 0
    assert captured["cookie_header"] == _FAKE_COOKIE_HEADER


def test_cli_cookie_file_env_variable_passes_header_to_pipeline(
    monkeypatch, tmp_path
):
    cookie_file = tmp_path / "env_cookie.txt"
    cookie_file.write_text(
        f"SESSDATA={_FAKE_COOKIE_VALUE}\nbili_jct=fake_csrf_value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BILI_COOKIE_FILE", str(cookie_file))
    captured = {}

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        captured["cookie_header"] = cookie_header
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["BV1xx411c7mD"])
    assert code == 0
    assert captured["cookie_header"] == _FAKE_COOKIE_HEADER


def test_cli_no_cookie_file_and_no_env_defaults_to_no_cookie(monkeypatch, tmp_path):
    monkeypatch.delenv("BILI_COOKIE_FILE", raising=False)
    captured = {}

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        captured["cookie_header"] = cookie_header
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["BV1xx411c7mD"])
    assert code == 0
    assert captured["cookie_header"] is None


def test_cli_missing_cookie_file_returns_non_zero(monkeypatch, tmp_path):
    monkeypatch.delenv("BILI_COOKIE_FILE", raising=False)
    monkeypatch.setattr(
        "bili_copilot.cli.run_pipeline",
        lambda input_url, output_base, cookie_header=None: tmp_path / "output_dir",
    )

    code = main(["BV1xx411c7mD", "--cookie-file", str(tmp_path / "missing.txt")])
    assert code != 0


def test_cli_empty_cookie_file_returns_non_zero(monkeypatch, tmp_path):
    cookie_file = tmp_path / "empty_cookie.txt"
    cookie_file.write_text("", encoding="utf-8")
    monkeypatch.delenv("BILI_COOKIE_FILE", raising=False)

    code = main(["BV1xx411c7mD", "--cookie-file", str(cookie_file)])
    assert code != 0


def test_cli_cookie_error_output_does_not_contain_cookie_value(
    capsys, monkeypatch, tmp_path
):
    cookie_file = tmp_path / "bad_cookie.txt"
    cookie_file.write_text(
        f"SESSDATA={_FAKE_COOKIE_VALUE}\nmalformed_line_no_equals\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("BILI_COOKIE_FILE", raising=False)

    code = main(["BV1xx411c7mD", "--cookie-file", str(cookie_file)])
    captured = capsys.readouterr()

    assert code != 0
    assert _FAKE_COOKIE_VALUE not in captured.out
    assert _FAKE_COOKIE_VALUE not in captured.err


def test_cli_success_output_does_not_contain_cookie_value(
    capsys, monkeypatch, tmp_path
):
    cookie_file = tmp_path / "bili_cookie.txt"
    cookie_file.write_text(
        f"SESSDATA={_FAKE_COOKIE_VALUE}\nbili_jct=fake_csrf_value\n",
        encoding="utf-8",
    )

    def fake_run_pipeline(input_url, output_base, cookie_header=None):
        return tmp_path / "output_dir"

    monkeypatch.setattr("bili_copilot.cli.run_pipeline", fake_run_pipeline)

    code = main(["BV1xx411c7mD", "--cookie-file", str(cookie_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert _FAKE_COOKIE_VALUE not in captured.out
    assert "fake_csrf_value" not in captured.out


def test_cli_help_does_not_contain_real_cookie_example(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    captured = capsys.readouterr()
    assert "SESSDATA=" not in captured.out
    assert "fake_session_value" not in captured.out
