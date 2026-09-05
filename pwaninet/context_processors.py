"""
Context processors for PwaniNet.
Provides global template variables.
"""
from pwaninet import version
from releases.services import ReleaseService


def release_metadata(request):
    """
    Inject release metadata into all templates.
    Provides version, build, and environment information from the current Release model.
    This is the single source of truth for version information in templates.
    
    Context variables:
        app_version: Application version string
        app_build: Build number
        app_environment: Environment (development/staging/production)
        app_release_date: Release date timestamp
        app_git_commit: Git commit hash (if available)
        app_git_branch: Git branch name (if available)
        current_release: Current Release object (if available)
        app_release_channel: Release channel (stable/beta/canary)
        app_mandatory_update: Whether this is a mandatory update
    """
    # Try to get current release from ReleaseService
    try:
        current_release = ReleaseService.get_current_release()
    except Exception:
        current_release = None
    
    if current_release:
        # Use Release model as source of truth
        return {
            'app_version': current_release.version,
            'app_build': current_release.build_number,
            'app_environment': version.__environment__,  # Still use version.py for environment
            'app_release_date': current_release.release_date,
            'app_git_commit': version.__git_commit__,
            'app_git_branch': version.__git_branch__,
            'current_release': current_release,
            'app_release_channel': current_release.get_release_channel_display(),
            'app_mandatory_update': current_release.mandatory_update,
        }
    else:
        # Fallback to version.py if no current release exists
        return {
            'app_version': version.__version__,
            'app_build': version.__build_number__,
            'app_environment': version.__environment__,
            'app_release_date': version.__release_date__,
            'app_git_commit': version.__git_commit__,
            'app_git_branch': version.__git_branch__,
            'current_release': None,
            'app_release_channel': None,
            'app_mandatory_update': False,
        }
