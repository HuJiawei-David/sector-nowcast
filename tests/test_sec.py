import json
from pathlib import Path

import pytest

from nowcast import sec

ROOT = Path(__file__).resolve().parents[1]


def test_user_agent_env_then_dotenv_then_error(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    monkeypatch.delenv(sec.ENV_VAR, raising=False)
    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        sec.user_agent(env)
    env.write_text("# comment\nOTHER=x\nSEC_USER_AGENT=\"Jane Doe jane@example.com\"\n")
    assert sec.user_agent(env) == "Jane Doe jane@example.com"
    monkeypatch.setenv(sec.ENV_VAR, "Env Name env@example.com")
    assert sec.user_agent(env) == "Env Name env@example.com"


def test_redact_email():
    assert sec.redact_email("Jane Doe jane.doe+x@example.co.uk") == "Jane Doe <redacted: SEC contact email>"


def test_no_contact_email_in_request_records():
    for f in (ROOT / "data" / "raw").rglob("*.request.json"):
        ua = json.loads(f.read_text()).get("headers", {}).get("User-Agent", "")
        assert "@" not in ua, f
