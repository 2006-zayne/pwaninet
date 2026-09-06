"""
Views for Unified Search in Pwaninet.
Handles live typing suggestions dropdown and multi-tab dedicated search page.
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .services.unified_search_service import UnifiedSearchService

logger = logging.getLogger(__name__)


def search_suggest_view(request):
    """
    Handle live typing suggestions for the navbar search dropdown.
    Returns floating preview results without affecting main feed or page layout.
    """
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return HttpResponse("")

    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    service = UnifiedSearchService()
    data = service.search(
        query=query,
        active_tab='all',
        user=user,
        page=1,
        page_size=3
    )

    following_ids = set()
    liked_post_ids = set()
    if user:
        from users.models import Follow
        from posts.models import Like
        following_ids = set(Follow.objects.filter(follower=user).values_list('followed_id', flat=True))
        post_ids = [
            item['obj'].id if isinstance(item, dict) and 'obj' in item and item['obj'] else item.get('id')
            for item in data['results']['posts']
        ]
        post_ids = [pid for pid in post_ids if pid]
        if post_ids:
            liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))

    context = {
        'query': query,
        'results': data['results'],
        'counts': data['counts'],
        'following_ids': following_ids,
        'liked_post_ids': liked_post_ids,
    }
    return render(request, 'search/partials/search_dropdown_results.html', context)


def unified_search_view(request):
    """
    Handle dedicated multi-tab search results page and tab switching.
    Supports HTMX partial swaps (page navigation vs tab content) and full page loads.
    """
    query = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'all').strip().lower()
    if tab not in ('all', 'people', 'documents', 'posts', 'groups'):
        tab = 'all'

    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    service = UnifiedSearchService()
    data = service.search(
        query=query,
        active_tab=tab,
        user=user,
        page=page,
        page_size=15
    )

    # Return JSON if requested
    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse(data)

    following_ids = set()
    liked_post_ids = set()
    unread_count = 0
    if user:
        from users.models import Follow
        from posts.models import Like
        following_ids = set(Follow.objects.filter(follower=user).values_list('followed_id', flat=True))
        post_ids = [
            item['obj'].id if isinstance(item, dict) and 'obj' in item and item['obj'] else item.get('id')
            for item in data['results']['posts']
        ]
        post_ids = [pid for pid in post_ids if pid]
        if post_ids:
            liked_post_ids = set(Like.objects.filter(user=user, post_id__in=post_ids).values_list('post_id', flat=True))

        try:
            from notifications.services.notification_service import get_cached_unread_count
            unread_count = get_cached_unread_count(user)
        except Exception:
            pass

    # Save search to session if query exists
    if query:
        recent = request.session.get('global_recent_searches', [])
        if query in recent:
            recent.remove(query)
        recent.insert(0, query)
        request.session['global_recent_searches'] = recent[:8]

    recent_searches = request.session.get('global_recent_searches', [])

    # Did you mean is scoped strictly to the documents tab
    did_you_mean = service.get_document_did_you_mean(query) if (query and tab == 'documents') else None

    context = {
        'query': data['query'],
        'active_tab': data['active_tab'],
        'counts': data['counts'],
        'results': data['results'],
        'pagination': data['pagination'],
        'following_ids': following_ids,
        'liked_post_ids': liked_post_ids,
        'unread_notifications_count': unread_count,
        'did_you_mean': did_you_mean,
        'recent_searches': recent_searches,
    }

    # HTMX tab content switch only
    if request.headers.get('HX-Target') == 'search-tab-content':
        return render(request, 'search/partials/tab_content.html', context)

    # HTMX full SPA page transition
    if request.headers.get('HX-Target') == 'page-content-target':
        return render(request, 'search/partials/search_navigation_partial.html', context)

    # Standard browser request or fallback HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'search/partials/search_navigation_partial.html', context)

    return render(request, 'search/search_results.html', context)


def clear_recent_searches_view(request):
    """
    Clear global search recent searches from session.
    """
    request.session['global_recent_searches'] = []
    if request.headers.get('HX-Request'):
        return HttpResponse('<div id="search-recent-container"></div>')
    from django.shortcuts import redirect
    return redirect(request.META.get('HTTP_REFERER', '/search/'))

