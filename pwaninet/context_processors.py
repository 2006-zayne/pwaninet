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

    try:
        latest_release = ReleaseService.get_latest_release()
    except Exception:
        latest_release = None

    if latest_release:
        latest_app_version = latest_release.version
        latest_app_build = latest_release.build_number
    else:
        latest_app_version = getattr(version, 'resolve_latest_version', version.resolve_version)()
        latest_app_build = version.resolve_build_number()
    
    latest_apk_version = getattr(version, 'resolve_latest_apk_version', version.resolve_latest_version)()

    # Check if request comes from the Capacitor native Android app
    # Strict separation: ONLY true Android native app traffic is marked as native.
    # Web and PWA traffic is NEVER treated as a native app and proceeds independently.
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
    is_native_app = bool('PwaniNetApp/Android' in user_agent or (request and request.headers.get('X-Capacitor-Platform') == 'android'))

    client_installed_version = None
    if is_native_app:
        import re
        ua_match = re.search(r'PwaniNetApp/Android/([0-9\.]+)', user_agent)
        if ua_match:
            client_installed_version = ua_match.group(1)
        elif request and request.COOKIES.get('pwaninet_native_version'):
            client_installed_version = request.COOKIES.get('pwaninet_native_version')

    # Effective version determination:
    # 1. Web and PWA (not native): ALWAYS runs the latest web release independently!
    # 2. Native App: If latest_apk_version > client_installed_version, STICKS to client_installed_version.
    #    Otherwise, updates to latest_app_version (or client_installed_version if client is newer).
    from releases.utils import parse_version

    # Ensure latest_apk_version and latest_app_version are not lower than client_installed_version
    if client_installed_version:
        try:
            if parse_version(client_installed_version) > parse_version(latest_apk_version):
                latest_apk_version = client_installed_version
            if parse_version(client_installed_version) > parse_version(latest_app_version):
                latest_app_version = client_installed_version
        except Exception:
            pass

    is_native_update_available = False
    if is_native_app and client_installed_version:
        try:
            if parse_version(client_installed_version) < parse_version(latest_apk_version):
                effective_app_version = client_installed_version
                is_native_update_available = True
            else:
                effective_app_version = latest_app_version
                is_native_update_available = False
        except Exception:
            effective_app_version = latest_app_version
    else:
        # Web and PWA always run the latest release independently
        effective_app_version = current_release.version if (current_release and parse_version(current_release.version) >= parse_version(latest_app_version)) else latest_app_version
        is_native_update_available = False

    base_context = {
        'app_version': effective_app_version,
        'app_build': current_release.build_number if current_release else latest_app_build,
        'latest_app_version': latest_app_version,
        'latest_app_build': latest_app_build,
        'latest_apk_version': latest_apk_version,
        'is_native_app': bool(is_native_app),
        'client_installed_version': client_installed_version,
        'is_native_update_available': is_native_update_available,
        'latest_release': latest_release,
        'app_environment': version.__environment__,
        'app_release_date': current_release.release_date if current_release else version.__release_date__,
        'app_git_commit': version.__git_commit__,
        'app_git_branch': version.__git_branch__,
        'current_release': current_release,
        'app_release_channel': current_release.get_release_channel_display() if current_release else None,
        'app_mandatory_update': current_release.mandatory_update if current_release else False,
    }
    return base_context
