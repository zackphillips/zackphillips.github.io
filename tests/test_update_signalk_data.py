import json
import os
import subprocess
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import scripts.update_signalk_data as usd


def test_filter_stale_data_removes_old_values():
    now = datetime.now(UTC)
    stale_ts = (now - timedelta(minutes=61)).isoformat()
    blob = {
        "environment": {
            "wind": {
                "speedTrue": {
                    "value": 5,
                    "timestamp": stale_ts,
                    "meta": {"units": "m/s"},
                }
            }
        },
        "design": {
            "length": {"value": {"overall": 12}},
        },
    }
    filtered = usd.filter_stale_data(
        deepcopy(blob),
        max_age_minutes=60,
        reference_time=now,
    )
    wind_data = filtered["environment"]["wind"]["speedTrue"]
    assert "value" not in wind_data
    assert "timestamp" not in wind_data
    # Design section should remain untouched
    assert filtered["design"]["length"]["value"]["overall"] == 12


def test_filter_stale_data_keeps_recent_values():
    now = datetime.now(UTC)
    recent_ts = (now - timedelta(minutes=10)).isoformat()
    blob = {
        "navigation": {
            "speedOverGround": {
                "value": 2.5,
                "timestamp": recent_ts,
            }
        }
    }
    filtered = usd.filter_stale_data(
        deepcopy(blob),
        max_age_minutes=60,
        reference_time=now,
    )
    sog = filtered["navigation"]["speedOverGround"]
    assert sog["value"] == 2.5
    assert sog["timestamp"] == recent_ts


def test_run_on_dev_branch_writes_file_and_calls_git(tmp_path, test_branch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example",
            output_path=str(out),
            use_https=False,
            no_push=False,
        )

        assert out.exists()
        assert json.loads(out.read_text()) == {"ok": True}
        assert any(cmd[:3] == ["git", "commit", "--allow-empty"] for cmd in calls)
        assert any(cmd[:2] == ["git", "push"] for cmd in calls)
        assert not any(cmd[:2] == ["git", "reset"] for cmd in calls)


def test_https_conversion(tmp_path, test_branch):
    """Test that HTTP URLs are converted to HTTPS when use_https=True."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": "test"}

    class FakeRequests:
        @staticmethod
        def get(url):
            assert url.startswith("https://")
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com:3000/api",
            output_path=str(out),
            use_https=True,
            no_push=False,
        )

        assert out.exists()
        assert json.loads(out.read_text()) == {"data": "test"}


def test_no_push_mode(tmp_path, test_branch):
    """Test that git push is skipped when no_push=True."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": "test"}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com/api",
            output_path=str(out),
            use_https=False,
            no_push=True,
        )

        assert out.exists()
        push_calls = [cmd for cmd in calls if cmd[:2] == ["git", "push"]]
        assert len(push_calls) == 0


def test_push_deferred_when_offline(tmp_path, test_branch):
    """Push and fetch failures (offline) are caught; commit is preserved locally."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)
        if cmd[:2] in (["git", "push"], ["git", "fetch"]):
            raise subprocess.CalledProcessError(1, cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        # Should not raise even though all network ops fail
        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example",
            output_path=str(out),
            use_https=False,
            no_push=False,
        )

        assert out.exists()
        commit_calls = [cmd for cmd in calls if "commit" in cmd]
        assert len(commit_calls) > 0
        push_attempts = [cmd for cmd in calls if cmd[:2] == ["git", "push"]]
        assert len(push_attempts) >= 1


def test_push_rebases_on_diverged_remote(tmp_path, test_branch):
    """On non-fast-forward push failure, script fetches, rebases, and retries push."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    first_push_done = [False]
    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["git", "push"] and not first_push_done[0]:
            first_push_done[0] = True
            raise subprocess.CalledProcessError(1, cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example",
            output_path=str(out),
            use_https=False,
            no_push=False,
        )

        assert out.exists()
        assert any(cmd[:2] == ["git", "fetch"] for cmd in calls)
        assert any(cmd[:2] == ["git", "rebase"] for cmd in calls)
        push_calls = [cmd for cmd in calls if cmd[:2] == ["git", "push"]]
        assert len(push_calls) == 2


def test_push_aborts_rebase_on_conflict(tmp_path, test_branch):
    """When rebase hits a conflict, abort is called and the script continues."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["git", "push"]:
            raise subprocess.CalledProcessError(1, cmd)
        if cmd[:2] == ["git", "rebase"] and "--abort" not in cmd:
            raise subprocess.CalledProcessError(1, cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        usd.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example",
            output_path=str(out),
            use_https=False,
            no_push=False,
        )

        assert out.exists()
        abort_calls = [cmd for cmd in calls if cmd == ["git", "rebase", "--abort"]]
        assert len(abort_calls) == 1


def test_requests_error_handling(tmp_path, test_branch):
    """Test that requests errors are properly handled."""

    class FakeRequests:
        @staticmethod
        def get(url):
            raise Exception("Network error")

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch("scripts.update_signalk_data.requests", FakeRequests),
        patch("scripts.update_signalk_data.subprocess.run", side_effect=fake_run),
    ):
        out = tmp_path / "signalk_latest.json"

        try:
            usd.run_update(
                branch=test_branch,
                remote="origin",
                signalk_url="http://example.com/api",
                output_path=str(out),
                use_https=False,
                no_push=False,
            )
            raise Exception("Expected exception was not raised")
        except Exception as e:
            assert "Network error" in str(e)
            assert not out.exists()


def test_integration_updates_test_branch(tmp_path, test_branch):
    def run(cmd, cwd=None):
        subprocess.run(cmd, check=True, cwd=cwd)

    # Create a bare origin repo
    origin = tmp_path / "origin.git"
    origin.mkdir()
    run(["git", "init", "--bare"], cwd=origin)
    run(["git", "config", "user.email", "test@example.com"], cwd=origin)
    run(["git", "config", "user.name", "Test"], cwd=origin)

    # Seed repo to create branches on origin
    seed = tmp_path / "seed"
    seed.mkdir()
    run(["git", "init"], cwd=seed)
    (seed / "README.md").write_text("seed")
    run(["git", "add", "README.md"], cwd=seed)
    run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "init",
        ],
        cwd=seed,
    )
    run(["git", "remote", "add", "origin", str(origin)], cwd=seed)
    run(["git", "push", "-u", "origin", "master"], cwd=seed)
    # Create _test_branch_tmp branch and push
    run(["git", "checkout", "-b", test_branch], cwd=seed)
    run(["git", "push", "-u", "origin", test_branch], cwd=seed)

    # Working repo (what the script will operate on)
    work = tmp_path / "work"
    run(["git", "clone", str(origin), str(work)])

    # Fetch all remote branches and checkout test_branch branch
    run(["git", "fetch", "--all"], cwd=work)
    run(["git", "checkout", "-b", test_branch, f"origin/{test_branch}"], cwd=work)

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    with patch("scripts.update_signalk_data.requests", FakeRequests):
        out = work / "signalk_latest.json"

        original_cwd = os.getcwd()
        try:
            os.chdir(work)
            usd.run_update(
                branch=test_branch,
                remote="origin",
                signalk_url="http://example",
                output_path=str(out),
                use_https=False,
                no_push=False,
            )
        finally:
            os.chdir(original_cwd)

        assert out.exists()
        before_after = (
            subprocess.check_output(
                ["git", "ls-remote", str(origin), f"refs/heads/{test_branch}"]
            )
            .decode()
            .strip()
        )
        assert (
            before_after
        ), f"{test_branch} branch should exist on origin and have a commit"
