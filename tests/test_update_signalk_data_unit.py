import json
import sys


def test_run_on_dev_branch_writes_file_and_calls_git(tmp_path, monkeypatch):
    # Fake requests module to avoid dependency and network
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    monkeypatch.setitem(sys.modules, "requests", FakeRequests)

    # Capture subprocess.run calls
    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr("subprocess.run", fake_run)

    # Prepare module under test
    import importlib
    import sys
    from pathlib import Path
    
    # Add the project root to Python path
    sys.path.insert(0, str(Path.cwd()))
    
    mod = importlib.import_module("scripts.update_signalk_data")

    # Use a path inside tmp
    out = tmp_path / "signalk_latest.json"

    mod.run_update(
        branch="dev",
        remote="origin",
        signalk_url="http://example",  # mocked
        output_path=str(out),
        use_https=False,
        no_reset=False,
        amend=False,
        no_push=False,
        force_push=False,
    )

    assert out.exists()
    assert json.loads(out.read_text()) == {"ok": True}
    # Ensure reset targeted origin/_test_branch_tmp and commit without --amend --force
    assert ["git", "fetch", "--all"] in calls
    assert ["git", "reset", "--hard", "origin/_test_branch_tmp"] in calls
    assert any(cmd[:3] == ["git", "commit", "--allow-empty"] for cmd in calls)
    assert ["git", "push"] in calls
