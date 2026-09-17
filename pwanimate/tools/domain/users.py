"""
User Profile Tool for Pwanimate.

Allows deterministic, read-only retrieval of user profile metadata while
strictly enforcing profile privacy levels (Public, Authenticated, Followers, Private)
and masking sensitive authentication and contact attributes.
"""

from typing import Any, Dict, Optional
from django.contrib.auth import get_user_model

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolValidationError, ToolPermissionError, ToolNotFoundError
from users.models import PrivacyLevel, Follow

User = get_user_model()


class UserProfileTool(BaseDomainTool):
    """
    Look up a user's academic and public profile information.
    """
    name = "user_profile"
    description = (
        "Retrieve sanitized profile information for a PwaniNet user (academic details, "
        "bio, headline, skills) respecting user privacy settings."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username of the target user",
            },
            "user_id": {
                "type": "integer",
                "description": "Unique integer ID of the target user",
            },
        },
        "required": [],
    }

    def execute(
        self,
        user: Any,
        username: Optional[str] = None,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        if not username and not user_id:
            raise ToolValidationError(
                "Either 'username' or 'user_id' must be provided.",
                tool_name=self.name,
            )

        qs = User.objects.filter(is_active=True).select_related("course", "programme", "year")
        target_user = None
        if username:
            target_user = qs.filter(username__iexact=username.strip()).first()
        elif user_id:
            target_user = qs.filter(id=user_id).first()

        if not target_user:
            raise ToolNotFoundError(
                f"User not found or is inactive (username='{username}', user_id={user_id}).",
                tool_name=self.name,
            )

        is_auth = user is not None and getattr(user, "is_authenticated", False)
        is_self = is_auth and user.id == target_user.id
        is_staff = is_auth and getattr(user, "is_staff", False)

        # Privacy evaluation
        privacy = getattr(target_user, "profile_privacy", PrivacyLevel.PUBLIC)

        if not is_self and not is_staff:
            if privacy == PrivacyLevel.AUTHENTICATED and not is_auth:
                raise ToolPermissionError(
                    "You must be logged in to view this user's profile.",
                    tool_name=self.name,
                )
            elif privacy == PrivacyLevel.FOLLOWERS:
                if not is_auth:
                    raise ToolPermissionError(
                        "This profile is visible to followers only.",
                        tool_name=self.name,
                    )
                is_follower = Follow.objects.filter(follower=user, followed=target_user).exists()
                if not is_follower:
                    raise ToolPermissionError(
                        "This profile is visible to followers only.",
                        tool_name=self.name,
                    )
            elif privacy == PrivacyLevel.PRIVATE:
                raise ToolPermissionError(
                    "This profile is private.",
                    tool_name=self.name,
                )

        display_name = (
            f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
            or target_user.username
        )

        profile_photo_url = None
        if target_user.profile_pic:
            try:
                profile_photo_url = target_user.profile_pic.url
            except Exception:
                profile_photo_url = str(target_user.profile_pic)

        data: Dict[str, Any] = {
            "username": target_user.username,
            "display_name": display_name,
            "global_role": target_user.global_role,
            "headline": target_user.headline or "",
            "bio": target_user.bio or "",
            "course": target_user.course.name if target_user.course else None,
            "programme": target_user.programme.name if target_user.programme else None,
            "year": target_user.year.level if target_user.year else None,
            "interests": target_user.interests or "",
            "collaboration_status": target_user.collaboration_status or "",
            "skills": target_user.skills if isinstance(target_user.skills, list) else [],
            "profile_photo_url": profile_photo_url,
        }

        # Include email only if viewing own profile or staff
        if is_self or is_staff:
            data["email"] = target_user.email

        return ToolResult.ok(data, target_username=target_user.username)
