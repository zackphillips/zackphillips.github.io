"""Shared helpers for the vessel tracking scripts."""

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

VESSEL_INFO_PATH = "data/vessel/info.yaml"


class VesselConfigError(Exception):
    """Raised when vessel configuration is invalid or missing."""


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically.

    The Pi can lose power mid-write. A partial write leaves truncated JSON,
    which the index loaders treat as "no data" — silently discarding a day of
    history. Writing to a temp file in the same directory and renaming makes
    the update all-or-nothing: readers see either the old file or the new one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def get_project_root() -> Path:
    """The repo root (this file lives in scripts/)."""
    return Path(__file__).parent.parent


def load_vessel_info(info_path: str = VESSEL_INFO_PATH) -> dict[str, Any]:
    """Load vessel configuration from a YAML file relative to the repo root.

    Raises VesselConfigError if the file is missing or unparseable.
    """
    full_path = get_project_root() / info_path
    if not full_path.exists():
        raise VesselConfigError(f"Vessel info file not found: {full_path}")
    try:
        info = yaml.safe_load(full_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise VesselConfigError(f"Invalid YAML in {full_path}: {e}") from e
    if info is None:
        return {}
    if not isinstance(info, dict):
        raise VesselConfigError(
            f"Expected a mapping in {full_path}, got {type(info).__name__}"
        )
    return info


def save_vessel_info(info: dict[str, Any], info_path: str = VESSEL_INFO_PATH) -> bool:
    """Write vessel configuration back to YAML. Returns True on success."""
    full_path = get_project_root() / info_path
    try:
        atomic_write_text(
            full_path,
            yaml.dump(info, default_flow_style=False, sort_keys=False, indent=2),
        )
        return True
    except (OSError, yaml.YAMLError) as e:
        print(f"Failed to save vessel info to {full_path}: {e}")
        return False
