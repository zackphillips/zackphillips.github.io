import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import requests


SIGNALK_CHECK_ENV = os.getenv("SIGNALK_VERIFY_FOR_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
}


@pytest.fixture(autouse=True)
def check_signalk_running():
    """
    Autouse fixture that checks if SignalK is running on the specified port and URL
    from info.json before each test. This ensures tests only run when SignalK is available.
    """
    if not SIGNALK_CHECK_ENV:
        return
    # Read SignalK configuration from info.json
    info_path = Path(__file__).parent.parent / "data" / "vessel" / "info.json"

    if not info_path.exists():
        pytest.skip("info.json not found - cannot determine SignalK configuration")

    try:
        with open(info_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, KeyError) as e:
        pytest.skip(f"Failed to parse info.json: {e}")

    signalk_config = config.get("signalk", {})
    host = signalk_config.get("host")
    port = signalk_config.get("port")
    protocol = signalk_config.get("protocol", "http")

    if not host or not port:
        pytest.skip("SignalK host or port not configured in info.json")

    # Construct the SignalK URL
    signalk_url = f"{protocol}://{host}:{port}"

    # Check if SignalK is running by making a request to the server
    try:
        # Try to connect to SignalK with a reasonable timeout
        response = requests.get(f"{signalk_url}/signalk", timeout=5)
        if response.status_code == 200:
            # SignalK is running and responding
            return
        else:
            pytest.skip(f"SignalK responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        pytest.skip(f"SignalK is not running at {signalk_url}")
    except requests.exceptions.Timeout:
        pytest.skip(f"SignalK connection timeout at {signalk_url}")
    except Exception as e:
        pytest.skip(f"Failed to check SignalK status: {e}")


class TestBranchManager:
    """Manages a temporary test branch for testing purposes."""

    def __init__(
        self, original_repo_path, temp_repo_path, branch_name="_test_branch_tmp"
    ):
        self.original_repo_path = Path(original_repo_path)
        self.temp_repo_path = Path(temp_repo_path)
        self.branch_name = branch_name
        self.remote_name = "origin"

    def run_git(self, cmd, cwd=None, check=True):
        """Run a git command and return the result."""
        if cwd is None:
            cwd = self.temp_repo_path

        result = subprocess.run(
            ["git"] + cmd, cwd=cwd, capture_output=True, text=True, check=check
        )
        return result

    def setup_test_branch(self):
        """Create and setup the temporary test branch."""
        # Clean up any existing temporary branch
        self.cleanup_test_branch()

        # Create temporary directory and clone the repo
        if self.temp_repo_path.exists():
            shutil.rmtree(self.temp_repo_path)

        self.temp_repo_path.mkdir(parents=True, exist_ok=True)

        # Clone the current repo to temp location
        self.run_git(["clone", str(self.original_repo_path), str(self.temp_repo_path)])

        # Configure git user for commits
        self.run_git(["config", "user.name", "Test User"])
        self.run_git(["config", "user.email", "test@example.com"])

        # Create and checkout the test branch
        self.run_git(["checkout", "-b", self.branch_name])

        # Push the test branch to remote
        self.run_git(["push", "-u", self.remote_name, self.branch_name])

        return self.temp_repo_path

    def cleanup_test_branch(self):
        """Clean up the temporary test branch from both local and remote."""
        try:
            # Delete remote branch if it exists
            self.run_git(
                ["push", self.remote_name, "--delete", self.branch_name], check=False
            )
        except subprocess.CalledProcessError:
            # Branch might not exist on remote, which is fine
            pass

        try:
            # Delete local branch if it exists
            self.run_git(["branch", "-D", self.branch_name], check=False)
        except subprocess.CalledProcessError:
            # Branch might not exist locally, which is fine
            pass

        # Clean up temp directory
        if self.temp_repo_path.exists():
            shutil.rmtree(self.temp_repo_path)

    def get_repo_path(self):
        """Get the path to the temporary repository."""
        return self.temp_repo_path


@pytest.fixture
def test_branch_manager():
    """
    Fixture that provides a TestBranchManager instance for managing temporary test branches.

    Usage:
        def test_something(test_branch_manager):
            repo_path = test_branch_manager.setup_test_branch()
            # ... run tests ...
            # cleanup happens automatically after test
    """
    # Get the current repository path (assuming we're in the repo)
    current_repo = Path.cwd()

    # Create a temporary directory for the test repo
    temp_dir = Path(tempfile.mkdtemp(prefix="test_repo_"))

    # Create the branch manager
    manager = TestBranchManager(current_repo, temp_dir)

    # Setup the test branch
    manager.setup_test_branch()

    # Yield the manager to the test
    yield manager

    # Cleanup happens automatically after the test
    manager.cleanup_test_branch()


@pytest.fixture
def test_branch():
    """Fixture that returns the test branch name used across all tests."""
    return "_test_branch_tmp"
