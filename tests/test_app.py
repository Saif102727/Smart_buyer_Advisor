import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_app_renders_without_exceptions(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTBUYER_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("SMARTBUYER_MODEL_DIR", str(tmp_path / "models"))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception, at.exception


def test_invalid_input_shows_safe_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTBUYER_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("SMARTBUYER_MODEL_DIR", str(tmp_path / "models"))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.text_input[0].set_value("<script>alert(1)</script>")
    at.button[0].click().run()
    assert not at.exception, at.exception
