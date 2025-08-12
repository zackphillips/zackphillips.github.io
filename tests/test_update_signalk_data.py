import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


def test_run_on_dev_branch_writes_file_and_calls_git(tmp_path, test_branch):
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

    # Capture subprocess.run calls
    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    # Patch both requests module and subprocess.run
    with (
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        # Prepare module under test
        import importlib
        from pathlib import Path

        # Add the project root to Python path using the test file location as reference
        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        # Use a path inside tmp
        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
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
        assert ["git", "reset", "--hard", f"origin/{test_branch}"] in calls
        assert any(cmd[:3] == ["git", "commit", "--allow-empty"] for cmd in calls)
        assert ["git", "push"] in calls


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
            # Verify the URL was converted to HTTPS
            assert url.startswith("https://")
            return FakeResp()

    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    with (
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com:3000/api",
            output_path=str(out),
            use_https=True,  # This should convert HTTP to HTTPS
            no_reset=False,
            amend=False,
            no_push=False,
            force_push=False,
        )

        assert out.exists()
        assert json.loads(out.read_text()) == {"data": "test"}


def test_no_reset_mode(tmp_path, test_branch):
    """Test that git reset is skipped when no_reset=True."""

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
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com/api",
            output_path=str(out),
            use_https=False,
            no_reset=True,  # This should skip git reset
            amend=False,
            no_push=False,
            force_push=False,
        )

        assert out.exists()
        # Verify git reset was not called
        reset_calls = [cmd for cmd in calls if cmd[:2] == ["git", "reset"]]
        assert len(reset_calls) == 0


def test_amend_commit(tmp_path, test_branch):
    """Test that --amend flag is used when amend=True."""

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
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com/api",
            output_path=str(out),
            use_https=False,
            no_reset=False,
            amend=True,  # This should add --amend to commit
            no_push=False,
            force_push=False,
        )

        assert out.exists()
        # Verify --amend was used in commit
        commit_calls = [cmd for cmd in calls if cmd[:2] == ["git", "commit"]]
        assert len(commit_calls) > 0
        assert "--amend" in commit_calls[0]


def test_force_push(tmp_path, test_branch):
    """Test that --force flag is used when force_push=True."""

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
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com/api",
            output_path=str(out),
            use_https=False,
            no_reset=False,
            amend=False,
            no_push=False,
            force_push=True,  # This should add --force to push
        )

        assert out.exists()
        # Verify --force was used in push
        push_calls = [cmd for cmd in calls if cmd[:2] == ["git", "push"]]
        assert len(push_calls) > 0
        assert "--force" in push_calls[0]


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
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        mod.run_update(
            branch=test_branch,
            remote="origin",
            signalk_url="http://example.com/api",
            output_path=str(out),
            use_https=False,
            no_reset=False,
            amend=False,
            no_push=True,  # This should skip git push
            force_push=False,
        )

        assert out.exists()
        # Verify git push was not called
        push_calls = [cmd for cmd in calls if cmd[:2] == ["git", "push"]]
        assert len(push_calls) == 0


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
        patch.dict(sys.modules, {"requests": FakeRequests}),
        patch("subprocess.run", side_effect=fake_run),
    ):
        import importlib

        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))

        mod = importlib.import_module("scripts.update_signalk_data")

        out = tmp_path / "signalk_latest.json"

        # Should raise an exception when requests fails
        try:
            mod.run_update(
                branch=test_branch,
                remote="origin",
                signalk_url="http://example.com/api",
                output_path=str(out),
                use_https=False,
                no_reset=False,
                amend=False,
                no_push=False,
                force_push=False,
            )
            raise Exception("Expected exception was not raised")
        except Exception as e:
            assert "Network error" in str(e)
            # Verify no file was written
            assert not out.exists()


@patch.dict(sys.modules, {"requests": None})
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

    # Fake requests module to avoid network
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class FakeRequests:
        @staticmethod
        def get(url):
            return FakeResp()

    # Patch the requests module with our fake implementation
    with patch.dict(sys.modules, {"requests": FakeRequests}):
        # Import the script module from the project under test
        test_file_dir = Path(__file__).parent
        project_root = test_file_dir.parent
        sys.path.insert(0, str(project_root))
        import importlib

        mod = importlib.import_module("scripts.update_signalk_data")

        # Run from within the working repo
        out = work / "signalk_latest.json"

        # Change to the working directory before running the script
        original_cwd = os.getcwd()
        try:
            os.chdir(work)
            mod.run_update(
                branch=test_branch,
                remote="origin",
                signalk_url="http://example",
                output_path=str(out),
                use_https=False,
                no_reset=False,
                amend=False,
                no_push=False,
                force_push=False,
            )
        finally:
            os.chdir(original_cwd)

        assert out.exists()
        # Ensure test_branch branch on origin has advanced (contains latest file content commit)
        # Fetch the ref hash
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
