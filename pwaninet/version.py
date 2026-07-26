"""
PwaniNet Version Module
Single source of truth for application versioning and release metadata.
"""
import os
from datetime import datetime

# Application version (semantic versioning with optional pre-release tags)
__version__ = "1.0.0-beta.1"

# Build number - independent of version, increments on each deployment
__build_number__ = 1

# Environment - development, staging, or production
__environment__ = os.environ.get('PWANINET_ENV', 'development')

# Release date - when this version was deployed
__release_date__ = datetime.utcnow().isoformat() + 'Z'

# Git metadata (optional, populated during build if available)
__git_commit__ = os.environ.get('GIT_COMMIT', '')
__git_branch__ = os.environ.get('GIT_BRANCH', '')


def get_version_info():
    """
    Return complete version metadata as a dictionary.
    This is the single source of truth for all version information.
    
    Returns:
        dict: Complete version and build metadata
    """
    return {
        'version': __version__,
        'build_number': __build_number__,
        'environment': __environment__,
        'release_date': __release_date__,
        'git_commit': __git_commit__,
        'git_branch': __git_branch__,
    }
