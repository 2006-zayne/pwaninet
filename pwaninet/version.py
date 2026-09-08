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


_latest_version_cache = {"version": None, "timestamp": 0}


def fetch_github_latest_release(repo="2006-zayne/pwaninet", timeout=3):
    """
    Fetch the latest release tag from GitHub Releases API.
    Cached for 10 minutes to respect GitHub rate limits.
    """
    try:
        from django.core.cache import cache
        cached = cache.get(f'github_latest_release:{repo}')
        if cached:
            return cached
    except Exception:
        cache = None

    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases/latest',
            headers={'User-Agent': 'PwaniNet-App/1.0', 'Accept': 'application/vnd.github.v3+json'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                tag = data.get('tag_name', '').lstrip('v').strip()
                if tag:
                    if cache:
                        try:
                            cache.set(f'github_latest_release:{repo}', tag, timeout=600)
                        except Exception:
                            pass
                    return tag
    except Exception:
        pass
    return None


def resolve_latest_version(use_cache=True):
    """
    Resolve the latest version string from available releases, GitHub API, or git tags.
    Priority:
    1. Environment variable LATEST_APP_VERSION
    2. GitHub Releases API (latest published tag)
    3. Highest git tag via git tag --sort=-v:refname
    4. Fallback to resolve_version()
    """
    import time
    now = time.time()
    if use_cache and _latest_version_cache["version"] and (now - _latest_version_cache["timestamp"] < 300):
        return _latest_version_cache["version"]

    env_latest = os.environ.get('LATEST_APP_VERSION')
    if env_latest:
        ver = env_latest.lstrip('v').strip()
        _latest_version_cache["version"] = ver
        _latest_version_cache["timestamp"] = now
        return ver

    # Check GitHub Releases API
    gh_tag = fetch_github_latest_release()
    if gh_tag:
        _latest_version_cache["version"] = gh_tag
        _latest_version_cache["timestamp"] = now
        return gh_tag

    # Check local git tags
    git_tags = _run_git_command(["tag", "--sort=-v:refname"])
    if git_tags:
        for tag in git_tags.splitlines():
            clean_tag = tag.strip().lstrip('v').strip()
            if clean_tag:
                _latest_version_cache["version"] = clean_tag
                _latest_version_cache["timestamp"] = now
                return clean_tag

    fallback = resolve_version()
    _latest_version_cache["version"] = fallback
    _latest_version_cache["timestamp"] = now
    return fallback


NATIVE_PATHS = ['android/', 'package.json', 'package-lock.json', 'capacitor.config.json']

_latest_apk_version_cache = {"version": None, "timestamp": 0}


def fetch_github_latest_apk_release(repo="2006-zayne/pwaninet", timeout=3):
    """
    Fetch the latest release tag from GitHub Releases API that has an .apk asset attached.
    Cached for 10 minutes.
    """
    try:
        from django.core.cache import cache
        cached = cache.get(f'github_latest_apk_release:{repo}')
        if cached:
            return cached
    except Exception:
        cache = None

    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases',
            headers={'User-Agent': 'PwaniNet-App/1.0', 'Accept': 'application/vnd.github.v3+json'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                releases = json.loads(resp.read().decode('utf-8'))
                for r in releases:
                    assets = r.get('assets', [])
                    if any(a.get('name', '').endswith('.apk') for a in assets):
                        tag = r.get('tag_name', '').lstrip('v').strip()
                        if tag:
                            if cache:
                                try:
                                    cache.set(f'github_latest_apk_release:{repo}', tag, timeout=600)
                                except Exception:
                                    pass
                            return tag
    except Exception:
        pass
    return None


def resolve_latest_apk_version(use_cache=True):
    """
    Resolve the latest version that introduced Capacitor / native Android changes and has an APK.
    Priority:
    1. Environment variable LATEST_APK_VERSION
    2. Git tag of the most recent commit modifying native files (android/, package.json, capacitor config)
    3. GitHub Releases API (latest release with an .apk asset)
    4. Fallback to resolve_latest_version()
    """
    import time
    now = time.time()
    if use_cache and _latest_apk_version_cache["version"] and (now - _latest_apk_version_cache["timestamp"] < 300):
        return _latest_apk_version_cache["version"]

    env_apk = os.environ.get('LATEST_APK_VERSION')
    if env_apk:
        ver = env_apk.lstrip('v').strip()
        _latest_apk_version_cache["version"] = ver
        _latest_apk_version_cache["timestamp"] = now
        return ver

    # Check Git commit history for the latest tag that modified native files
    last_native_commit = _run_git_command(["log", "-n", "1", "--format=%H", "--"] + NATIVE_PATHS)
    if last_native_commit:
        native_tag = _run_git_command(["describe", "--tags", "--abbrev=0", last_native_commit])
        if native_tag:
            ver = native_tag.lstrip('v').strip()
            _latest_apk_version_cache["version"] = ver
            _latest_apk_version_cache["timestamp"] = now
            return ver

    # Check GitHub Releases API for releases with an APK asset
    gh_apk_tag = fetch_github_latest_apk_release()
    if gh_apk_tag:
        _latest_apk_version_cache["version"] = gh_apk_tag
        _latest_apk_version_cache["timestamp"] = now
        return gh_apk_tag

    fallback = resolve_latest_version(use_cache=use_cache)
    _latest_apk_version_cache["version"] = fallback
    _latest_apk_version_cache["timestamp"] = now
    return fallback


def has_native_changes(from_version, to_version=None):
    """
    Check whether any commits between from_version and to_version modified native Capacitor/Android files.
    """
    if not from_version:
        return True
    v_from = f"v{from_version.lstrip('v').strip()}"
    v_to = f"v{to_version.lstrip('v').strip()}" if to_version else "HEAD"
    diff = _run_git_command(["diff", "--name-only", f"{v_from}..{v_to}", "--"] + NATIVE_PATHS)
    return bool(diff and diff.strip())



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
