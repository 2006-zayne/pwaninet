"""
PwaniNet Version Module
Single source of truth for application versioning and release metadata.
Dynamically resolves version and build numbers from Git tags and environment,
matching the mobile app build releases automatically.
"""
import functools
import os
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_VERSION = "1.0.1"
DEFAULT_BUILD = 64

BASE_DIR = Path(__file__).resolve().parent.parent


def _run_git_command(args):
    """Run a git command safely and return stripped stdout or None."""
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
    Resolve semantic version string (e.g. '1.0.1').
    Priority:
    1. Environment variable APP_VERSION or VERSION_NAME
    2. Git tag via git describe --tags --abbrev=0 (stripping leading 'v')
    3. Fallback to DEFAULT_VERSION
    """
    env_ver = os.environ.get('APP_VERSION') or os.environ.get('VERSION_NAME')
    if env_ver:
        return env_ver.lstrip('v').strip()

    git_tag = _run_git_command(["describe", "--tags", "--abbrev=0"])
    if git_tag:
        return git_tag.lstrip('v').strip()

    return DEFAULT_VERSION


@functools.lru_cache(maxsize=1)
def resolve_build_number():
    """
    Resolve numeric build number for ordering.
    Priority:
    1. Environment variable APP_BUILD_NUMBER, VERSION_CODE or GITHUB_RUN_NUMBER
    2. Git commit count: git rev-list --count HEAD
    3. Fallback to DEFAULT_BUILD
    """
    env_build = os.environ.get('APP_BUILD_NUMBER') or os.environ.get('VERSION_CODE') or os.environ.get('GITHUB_RUN_NUMBER')
    if env_build:
        try:
            return int(env_build)
        except ValueError:
            pass

    git_count = _run_git_command(["rev-list", "--count", "HEAD"])
    if git_count:
        try:
            return int(git_count)
        except ValueError:
            pass

    return DEFAULT_BUILD


@functools.lru_cache(maxsize=1)
def resolve_git_commit():
    """Resolve short Git commit hash."""
    return os.environ.get('GIT_COMMIT') or _run_git_command(["rev-parse", "--short", "HEAD"]) or ""


@functools.lru_cache(maxsize=1)
def resolve_git_branch():
    """Resolve current Git branch."""
    return os.environ.get('GIT_BRANCH') or _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]) or ""


# Module-level exports for backwards compatibility
__version__ = resolve_version()
__build_number__ = resolve_build_number()
__environment__ = os.environ.get('PWANINET_ENV', 'development')
__release_date__ = datetime.utcnow().isoformat() + 'Z'
__git_commit__ = resolve_git_commit()
__git_branch__ = resolve_git_branch()


def get_version_info():
    """
    Return complete version metadata as a dictionary.
    This is the single source of truth for all version information.
    """
    return {
        'version': resolve_version(),
        'build_number': resolve_build_number(),
        'environment': os.environ.get('PWANINET_ENV', 'development'),
        'release_date': __release_date__,
        'git_commit': resolve_git_commit(),
        'git_branch': resolve_git_branch(),
    }
