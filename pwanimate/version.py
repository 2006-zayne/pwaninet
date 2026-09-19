"""
Pwanimate Version Module.

Single source of truth for Pwanimate assistant versioning and release metadata.
Supports dynamic environment overrides, Git subsystem tag discovery, and
graceful fallback to semantic release defaults.
"""

import functools
import os
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_VERSION = "2.0.0"
BASE_DIR = Path(__file__).resolve().parent.parent


def _run_git_command(args):
    """Safely execute a git command and return stripped output or None."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


@functools.lru_cache(maxsize=1)
def resolve_version():
    """
    Resolve semantic version string for Pwanimate.

    Priority:
    1. Environment variable PWANIMATE_VERSION
    2. Git tag matching 'pwanimate-v*' pattern (e.g. 'pwanimate-v2.1.0' -> '2.1.0')
    3. Fallback to DEFAULT_VERSION ('2.0.0')
    """
    env_ver = os.environ.get("PWANIMATE_VERSION")
    if env_ver:
        return env_ver.lstrip("v").strip()

    git_tag = _run_git_command(["describe", "--tags", "--match=pwanimate-v*", "--abbrev=0"])
    if git_tag:
        clean = git_tag.replace("pwanimate-v", "").lstrip("v").strip()
        if clean:
            return clean

    return DEFAULT_VERSION


__version__ = resolve_version()


def get_version():
    """Return the current Pwanimate version string."""
    return resolve_version()


def get_version_info():
    """Return comprehensive metadata for Pwanimate assistant subsystem."""
    return {
        "version": resolve_version(),
        "subsystem": "pwanimate",
        "default_version": DEFAULT_VERSION,
        "environment": os.environ.get("PWANINET_ENV", "development"),
        "release_date": datetime.utcnow().isoformat() + "Z",
    }


def clear_version_cache():
    """Clear cached version to reflect runtime or environment changes."""
    resolve_version.cache_clear()
    global __version__
    __version__ = resolve_version()
