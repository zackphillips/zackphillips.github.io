import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from utils import get_project_root

# requests is imported at runtime inside fetch_blob to make unit testing easier

DEFAULT_OUTPUT_FILE = "./data/telemetry/signalk_latest.json"


def load_vessel_data() -> dict:
    """Load vessel configuration from JSON file."""
    try:
        vessel_file = Path("data/vessel/info.json")
        if vessel_file.exists():
            with open(vessel_file) as f:
                vessel_data = json.load(f)

            # Construct SignalK URL from vessel data
            signalk = vessel_data.get("signalk", {})
            if signalk.get("host") and signalk.get("port"):
                protocol = signalk.get("protocol", "http")
                host = signalk["host"]
                port = signalk["port"]
                return {
                    "signalk_url": f"{protocol}://{host}:{port}/signalk/v1/api/vessels/self",
                    "vessel_data": vessel_data,
                }
    except Exception as e:
        print(f"Warning: Could not load vessel data: {e}")

    # Fallback to default
    return {
        "signalk_url": "http://localhost:3000/signalk/v1/api/vessels/self",
        "vessel_data": {},
    }


def parse_args() -> SimpleNamespace:
    # Load vessel data first to get default SignalK URL
    vessel_config = load_vessel_data()

    parser = argparse.ArgumentParser(description="Fetch SignalK data and commit to git")
    parser.add_argument("--branch", default=os.getenv("GIT_BRANCH", "main"))
    parser.add_argument("--remote", default=os.getenv("GIT_REMOTE", "origin"))
    parser.add_argument(
        "--signalk-url",
        dest="signalk_url",
        default=os.getenv("SIGNALK_URL", vessel_config["signalk_url"]),
        help="SignalK API URL (defaults to vessel config or http://localhost:3000/signalk/v1/api/vessels/self)",
    )
    parser.add_argument(
        "--output", dest="output", default=os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)
    )
    parser.add_argument(
        "--use-https",
        dest="use_https",
        action="store_true",
        default=os.getenv("USE_HTTPS", "false").lower() == "true",
        help="Use HTTPS instead of HTTP for SignalK connection",
    )
    parser.add_argument(
        "--no-reset",
        dest="no_reset",
        action="store_true",
        default=os.getenv("NO_RESET", "false").lower() == "true",
    )
    parser.add_argument(
        "--no-push",
        dest="no_push",
        action="store_true",
        default=os.getenv("NO_PUSH", "false").lower() == "true",
    )
    parser.add_argument(
        "--amend",
        dest="amend",
        action="store_true",
        default=os.getenv("GIT_AMEND", "true").lower() == "true",
    )
    parser.add_argument(
        "--force-push",
        dest="force_push",
        action="store_true",
        default=os.getenv("GIT_FORCE_PUSH", "true").lower() == "true",
    )
    return parser.parse_args()


def fetch_blob(signalk_url: str) -> dict:
    import requests  # imported here to ease mocking in unit tests

    response = requests.get(signalk_url)
    response.raise_for_status()
    return response.json()


def git_reset(remote: str, branch: str) -> None:
    subprocess.run(["git", "fetch", "--all"], check=True)
    subprocess.run(["git", "reset", "--hard", f"{remote}/{branch}"], check=True)


def git_commit_and_push(
    file_path: Path, amend: bool, no_push: bool, force_push: bool
) -> None:
    subprocess.run(["git", "add", str(file_path)], check=True)
    commit_cmd = ["git", "commit", "-m", f"Auto update {datetime.now().isoformat()}"]
    if amend:
        commit_cmd.insert(2, "--amend")
    # allow empty to avoid failures when content is unchanged
    commit_cmd.insert(2, "--allow-empty")
    subprocess.run(commit_cmd, check=True)
    if not no_push:
        push_cmd = ["git", "push"]
        if force_push:
            push_cmd.append("--force")
        subprocess.run(push_cmd, check=True)


def run_update(
    branch: str,
    remote: str,
    signalk_url: str,
    output_path: str,
    use_https: bool,
    no_reset: bool,
    amend: bool,
    no_push: bool,
    force_push: bool,
) -> Path:
    # Modify SignalK URL if use_https is specified
    if use_https and signalk_url.startswith("http://"):
        signalk_url = signalk_url.replace("http://", "https://", 1)

    # Resolve output path against project root if not absolute
    output_file = Path(output_path)
    if not output_file.is_absolute():
        output_file = get_project_root() / output_file
    output_file = output_file.resolve()

    # Ensure destination directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if not no_reset:
        git_reset(remote=remote, branch=branch)
    blob = fetch_blob(signalk_url=signalk_url)
    output_file.write_text(json.dumps(blob, indent=2))
    print(f"Wrote SignalK blob to {output_file}")
    git_commit_and_push(
        file_path=output_file, amend=amend, no_push=no_push, force_push=force_push
    )
    return output_file


def main() -> int:
    try:
        args = parse_args()
        run_update(
            branch=args.branch,
            remote=args.remote,
            signalk_url=args.signalk_url,
            output_path=args.output,
            use_https=args.use_https,
            no_reset=args.no_reset,
            amend=args.amend,
            no_push=args.no_push,
            force_push=args.force_push,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level safety
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
