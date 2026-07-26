"""
Semantic version utilities for PwaniNet Release Center.

Provides reusable helpers for version parsing, comparison, and generation.
Follows semantic versioning specification (semver.org).
"""
import re
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class Version:
    """
    Represents a semantic version with optional pre-release and build metadata.
    
    Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    Examples:
        1.0.0
        1.0.1-hotfix.1
        1.1.0-beta.1
        2.0.0-rc.1+build.123
    """
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None
    
    def __str__(self) -> str:
        """Convert version to string representation"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version
    
    def __eq__(self, other) -> bool:
        """Compare versions for equality"""
        if not isinstance(other, Version):
            return False
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )
    
    def __lt__(self, other) -> bool:
        """Compare versions for less than"""
        if not isinstance(other, Version):
            return NotImplemented
        
        # Compare numeric parts
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        
        # Compare prerelease
        # Pre-release versions have lower precedence than normal versions
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is None and other.prerelease is None:
            return False
        
        # Compare prerelease identifiers
        self_parts = self._parse_prerelease(self.prerelease)
        other_parts = self._parse_prerelease(other.prerelease)
        
        for self_part, other_part in zip(self_parts, other_parts):
            result = self._compare_prerelease_identifiers(self_part, other_part)
            if result != 0:
                return result < 0
        
        # If all compared parts are equal, the longer version is greater
        return len(self_parts) < len(other_parts)
    
    def _parse_prerelease(self, prerelease: str) -> list:
        """Parse prerelease string into identifiers"""
        return prerelease.split('.')
    
    def _compare_prerelease_identifiers(self, a: str, b: str) -> int:
        """Compare two prerelease identifiers"""
        # Try to compare as numbers
        try:
            a_num = int(a)
            b_num = int(b)
            return a_num - b_num
        except ValueError:
            # Compare as strings
            if a < b:
                return -1
            elif a > b:
                return 1
            return 0
    
    def increment(self, release_type: str) -> 'Version':
        """
        Increment version based on release type.
        
        Args:
            release_type: One of 'MAJOR', 'MINOR', 'PATCH', 'HOTFIX'
        
        Returns:
            New Version instance with incremented values
        """
        if release_type == 'MAJOR':
            return Version(
                major=self.major + 1,
                minor=0,
                patch=0,
                prerelease=None,
                build=None
            )
        elif release_type == 'MINOR':
            return Version(
                major=self.major,
                minor=self.minor + 1,
                patch=0,
                prerelease=None,
                build=None
            )
        elif release_type in ('PATCH', 'HOTFIX'):
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch + 1,
                prerelease=None,
                build=None
            )
        else:
            raise ValueError(f"Invalid release type: {release_type}")


def parse_version(version_string: str) -> Version:
    """
    Parse a version string into a Version object.
    
    Args:
        version_string: Version string to parse (e.g., "1.0.0", "1.0.1-beta.1")
    
    Returns:
        Version object
    
    Raises:
        ValueError: If version string is invalid
    """
    # Remove build metadata if present
    if '+' in version_string:
        version_string, build = version_string.split('+', 1)
    else:
        build = None
    
    # Split version and prerelease
    if '-' in version_string:
        version_part, prerelease = version_string.split('-', 1)
    else:
        version_part = version_string
        prerelease = None
    
    # Parse numeric version
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_part)
    if not match:
        raise ValueError(f"Invalid version format: {version_string}")
    
    major, minor, patch = map(int, match.groups())
    
    return Version(
        major=major,
        minor=minor,
        patch=patch,
        prerelease=prerelease,
        build=build
    )


def increment_version(version_string: str, release_type: str) -> str:
    """
    Increment a version string based on release type.
    
    Args:
        version_string: Current version string
        release_type: One of 'MAJOR', 'MINOR', 'PATCH', 'HOTFIX'
    
    Returns:
        New version string
    
    Example:
        >>> increment_version("1.0.0", "MINOR")
        "1.1.0"
        >>> increment_version("1.0.0-beta.1", "PATCH")
        "1.0.1"
    """
    version = parse_version(version_string)
    new_version = version.increment(release_type)
    return str(new_version)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Args:
        v1: First version string
        v2: Second version string
    
    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    version1 = parse_version(v1)
    version2 = parse_version(v2)
    
    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    return 0


def is_version_greater(v1: str, v2: str) -> bool:
    """Check if v1 is greater than v2"""
    return compare_versions(v1, v2) > 0


def is_version_less(v1: str, v2: str) -> bool:
    """Check if v1 is less than v2"""
    return compare_versions(v1, v2) < 0


def validate_version(version_string: str) -> bool:
    """
    Validate a version string format.
    
    Args:
        version_string: Version string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_version(version_string)
        return True
    except ValueError:
        return False


def get_next_build_number(current_build: int) -> int:
    """
    Get the next build number.
    
    Args:
        current_build: Current build number
    
    Returns:
        Next build number (always increments)
    """
    return current_build + 1


def format_version_with_channel(version: str, channel: str) -> str:
    """
    Format version with release channel as prerelease tag.
    
    Args:
        version: Base version (e.g., "1.0.0")
        channel: Release channel (e.g., "BETA", "ALPHA")
    
    Returns:
        Version string with channel tag
    
    Example:
        >>> format_version_with_channel("1.0.0", "BETA")
        "1.0.0-beta.1"
    """
    if channel == 'STABLE':
        return version
    
    channel_map = {
        'DEVELOPMENT': 'dev',
        'ALPHA': 'alpha',
        'BETA': 'beta',
        'RELEASE_CANDIDATE': 'rc'
    }
    
    channel_tag = channel_map.get(channel, channel.lower())
    return f"{version}-{channel_tag}.1"


def extract_base_version(version_string: str) -> str:
    """
    Extract base version without prerelease or build metadata.
    
    Args:
        version_string: Full version string
    
    Returns:
        Base version (MAJOR.MINOR.PATCH)
    
    Example:
        >>> extract_base_version("1.0.0-beta.1+build.123")
        "1.0.0"
    """
    # Remove build metadata
    if '+' in version_string:
        version_string = version_string.split('+')[0]
    
    # Remove prerelease
    if '-' in version_string:
        version_string = version_string.split('-')[0]
    
    return version_string
