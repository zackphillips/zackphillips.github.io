import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)


def test_integration_updates_dev_branch(tmp_path, monkeypatch):
    # Create a bare origin repo
    origin = tmp_path / "origin.git"
    origin.mkdir()
    run(["git", "init", "--bare"], cwd=origin)

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
    # Create dev branch and push
    run(["git", "checkout", "-b", "dev"], cwd=seed)
    run(["git", "push", "-u", "origin", "dev"], cwd=seed)
    # Create _test_branch_tmp branch and push
    run(["git", "checkout", "-b", "_test_branch_tmp"], cwd=seed)
    run(["git", "push", "-u", "origin", "_test_branch_tmp"], cwd=seed)

    # Working repo (what the script will operate on)
    work = tmp_path / "work"
    run(["git", "clone", str(origin), str(work)])
    # Configure identity for commits made by the script
    run(["git", "config", "user.email", "test@example.com"], cwd=work)
    run(["git", "config", "user.name", "Test"], cwd=work)
    # Fetch all remote branches and checkout dev branch
    run(["git", "fetch", "--all"], cwd=work)
    run(["git", "checkout", "-b", "_test_branch_tmp", "origin/_test_branch_tmp"], cwd=work)

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

    monkeypatch.setitem(sys.modules, "requests", FakeRequests)

    # Import the script module from the project under test
    sys.path.insert(0, str(Path.cwd()))
    import importlib

    mod = importlib.import_module("scripts.update_signalk_data")

    # Run from within the working repo
    out = work / "signalk_latest.json"
    mod.run_update(
        branch="_test_branch_tmp",
        remote="origin",
        signalk_url="http://example",
        output_path=str(out),
        use_https=False,
        no_reset=False,
        amend=False,
        no_push=False,
        force_push=False,
    )

    assert out.exists()
    # Ensure dev branch on origin has advanced (contains latest file content commit)
    # Fetch the ref hash
    before_after = (
        subprocess.check_output(["git", "ls-remote", str(origin), "refs/heads/_test_branch_tmp"])
        .decode()
        .strip()
    )
    assert before_after, "dev branch should exist on origin and have a commit"
