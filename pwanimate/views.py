"""
Pwanimate UI Views.

Exposes authenticated template-backed endpoints for the Pwanimate assistant interface,
supporting both full-page browser loads and HTMX partial swaps.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from pwanimate.models import PwanimateConversation


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

        initial_prompt = request.GET.get("prompt", "").strip()

        context = {
            "conversations": user_conversations,
            "active_conversation": active_conversation,
            "active_conversation_id": str(active_conversation.id) if active_conversation else "",
            "messages": messages,
            "initial_prompt": initial_prompt,
        }

        hx_target = request.headers.get("HX-Target")
        if request.headers.get("HX-Request") and hx_target == "page-content-target":
            return render(request, "pwanimate/partials/chat_content.html", context)
        return render(request, "pwanimate/index.html", context)
