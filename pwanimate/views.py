"""
Pwanimate UI Views.

Exposes authenticated template-backed endpoints for the Pwanimate assistant interface,
supporting both full-page browser loads and HTMX partial swaps.
"""

from typing import Any, Dict, Optional

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from pwanimate.models import (
    PwanimateConversation,
    PwanimatePreferences,
    PwanimateResponseStyle,
    PwanimateTone,
)
from pwanimate.services.preferences import PwanimatePreferenceService
from pwanimate.version import get_version as get_pwanimate_version


def _get_settings_context(
    request: HttpRequest,
    active_tab: str = "personalization",
    success: bool = False,
    errors: Optional[Dict[str, Any]] = None,
    prefs: Optional[PwanimatePreferences] = None,
) -> Dict[str, Any]:
    """
    Construct standardized, unified settings context ensuring preferences,
    choices, usage telemetry, and version are always available.
    """
    if prefs is None:
        prefs = PwanimatePreferenceService.get_or_create_preferences(request.user)
    conversations_count = request.user.pwanimate_conversations.count()
    full_name = request.user.get_full_name().strip()
    user_display = full_name if full_name and full_name != "None None" else request.user.username
    return {
        "preferences": prefs,
        "tone_choices": PwanimateTone.choices,
        "response_style_choices": PwanimateResponseStyle.choices,
        "conversations_count": conversations_count,
        "user_display": user_display,
        "active_tab": active_tab,
        "success": success,
        "errors": errors or {},
        "pwanimate_version": get_pwanimate_version(),
    }


class PwanimateUIView(View):
    """
    Main user-facing view for Pwanimate.

    Renders the two-pane assistant workspace.
    If conversation_id is supplied, validates ownership and loads historical messages.
    Supports both direct full-page loads and HTMX inner swaps.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest, conversation_id=None) -> HttpResponse:
        active_conversation = None
        messages = []

        if conversation_id:
            try:
                active_conversation = PwanimateConversation.objects.get(
                    id=conversation_id,
                    user=request.user,
                )
                messages = list(active_conversation.messages.all().order_by("created_at"))
            except PwanimateConversation.DoesNotExist:
                raise Http404("Conversation not found.")

        user_conversations = PwanimateConversation.objects.filter(
            user=request.user
        ).order_by("-updated_at")

        paginator = Paginator(user_conversations, 15)
        page_obj = paginator.get_page(1)

        initial_prompt = request.GET.get("prompt", "").strip()

        settings_ctx = _get_settings_context(request)
        context = {
            **settings_ctx,
            "conversations": page_obj.object_list,
            "has_next": page_obj.has_next(),
            "next_page": 2 if page_obj.has_next() else None,
            "active_conversation": active_conversation,
            "active_conversation_id": str(active_conversation.id) if active_conversation else "",
            "messages": messages,
            "initial_prompt": initial_prompt,
        }

        if request.headers.get("HX-Request"):
            return render(request, "pwanimate/partials/chat_navigation_partial.html", context)
        return render(request, "pwanimate/index.html", context)


class PwanimateConversationHistoryView(View):
    """
    Paginated conversation history partial endpoint for infinite scroll lazy loading.
    Accepts page and active_id query parameters.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        page = request.GET.get("page", 1)
        active_id = request.GET.get("active_id", "").strip()

        user_conversations = PwanimateConversation.objects.filter(
            user=request.user
        ).order_by("-updated_at")

        paginator = Paginator(user_conversations, 15)
        try:
            page_obj = paginator.get_page(page)
        except Exception:
            page_obj = paginator.get_page(1)

        context = {
            "conversations": page_obj.object_list,
            "has_next": page_obj.has_next(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "active_conversation_id": active_id,
            "is_paginated_chunk": True,
        }
        return render(request, "pwanimate/partials/conversation_list.html", context)


class PwanimateConversationDeleteView(View):
    """
    Delete a conversation thread owned by the authenticated user.
    Returns 204 No Content on success, or 404 if not found or unauthorized.
    Supports both DELETE and POST methods (e.g. from HTMX or fetch).
    """

    @method_decorator(login_required)
    def delete(self, request: HttpRequest, conversation_id) -> HttpResponse:
        from pwanimate.services.conversation import ConversationService

        conversation = ConversationService.get_owned_conversation(
            user=request.user,
            conversation_id=conversation_id,
        )
        if conversation is None:
            raise Http404("Conversation not found.")

        conversation.delete()
        return HttpResponse(status=204)

    @method_decorator(login_required)
    def post(self, request: HttpRequest, conversation_id) -> HttpResponse:
        return self.delete(request, conversation_id)


class PwanimateSettingsView(View):
    """
    Landing endpoint for Pwanimate settings.
    Redirects to the default personalization settings tab.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        return redirect("pwanimate:settings_personalization")


class PwanimateSettingsPersonalizationView(View):
    """
    View to display and update student AI preferences (nickname, tone, response style, instructions).
    Supports desktop modal body swaps, mobile page content swaps, and full-page loads.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        context = _get_settings_context(request, active_tab="personalization")
        hx_target = request.headers.get("HX-Target", "")
        if request.headers.get("HX-Request"):
            if hx_target in ("pwanimate-settings-modal-body", "pwanimate-settings-mobile-content", "pwanimate-personalization-form"):
                return render(request, "pwanimate/settings/partials/personalization_content.html", context)
            return render(request, "pwanimate/settings/partials/settings_mobile_page.html", context)
        return render(request, "pwanimate/settings/index.html", context)

    @method_decorator(login_required)
    def post(self, request: HttpRequest) -> HttpResponse:
        nickname = request.POST.get("nickname")
        tone = request.POST.get("tone")
        response_style = request.POST.get("response_style")
        personal_instructions = request.POST.get("personal_instructions")

        errors = {}
        success = False
        try:
            prefs = PwanimatePreferenceService.update_preferences(
                user=request.user,
                nickname=nickname,
                tone=tone,
                response_style=response_style,
                personal_instructions=personal_instructions,
            )
            success = True
        except ValidationError as exc:
            saved_prefs = PwanimatePreferenceService.get_preferences_or_defaults(request.user)
            prefs = PwanimatePreferences(
                user=request.user,
                nickname=nickname if nickname is not None else saved_prefs.nickname,
                tone=tone if tone in PwanimateTone.values else saved_prefs.tone,
                response_style=response_style if response_style in PwanimateResponseStyle.values else saved_prefs.response_style,
                personal_instructions=personal_instructions if personal_instructions is not None else saved_prefs.personal_instructions,
            )
            if hasattr(exc, "message_dict"):
                errors = exc.message_dict
            elif hasattr(exc, "messages"):
                errors = {"__all__": exc.messages}
            else:
                errors = {"__all__": [str(exc)]}

        context = _get_settings_context(
            request,
            active_tab="personalization",
            success=success,
            errors=errors,
            prefs=prefs,
        )

        if request.headers.get("HX-Request"):
            return render(request, "pwanimate/settings/partials/personalization_content.html", context)
        return render(request, "pwanimate/settings/index.html", context)


class PwanimateSettingsUsageView(View):
    """
    View displaying student usage context and accounting status.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        context = _get_settings_context(request, active_tab="usage")
        hx_target = request.headers.get("HX-Target", "")
        if request.headers.get("HX-Request"):
            if hx_target in ("pwanimate-settings-modal-body", "pwanimate-settings-mobile-content"):
                return render(request, "pwanimate/settings/partials/usage_content.html", context)
            return render(request, "pwanimate/settings/partials/settings_mobile_page.html", context)
        return render(request, "pwanimate/settings/index.html", context)


class PwanimateSettingsAboutView(View):
    """
    View displaying about information, capabilities, and boundaries for Pwanimate.
    """

    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        context = _get_settings_context(request, active_tab="about")
        hx_target = request.headers.get("HX-Target", "")
        if request.headers.get("HX-Request"):
            if hx_target in ("pwanimate-settings-modal-body", "pwanimate-settings-mobile-content"):
                return render(request, "pwanimate/settings/partials/about_content.html", context)
            return render(request, "pwanimate/settings/partials/settings_mobile_page.html", context)
        return render(request, "pwanimate/settings/index.html", context)

