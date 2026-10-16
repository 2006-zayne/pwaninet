"""Upload Manager page (Phase 3): account-wide upload history UI."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def manager_view(request):
    return render(request, "uploads/manager.html", {})
