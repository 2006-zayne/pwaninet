from django.shortcuts import render
from django.http import JsonResponse

def skeleton_preview(request, skeleton_name):
    """
    Preview skeleton loaders individually
    """
    skeleton_templates = {
        'post-feed': 'partials/_skeleton_post_feed.html',
        'profile': 'partials/_skeleton_profile.html',
        'groups-list': 'partials/_skeleton_groups_list.html',
        'notifications': 'partials/_skeleton_notifications.html',
    }
    
    template_name = skeleton_templates.get(skeleton_name)
    if not template_name:
        return JsonResponse({'error': 'Skeleton not found'}, status=404)
    
    return render(request, template_name)

def skeleton_template(request, template_name):
    """
    Serve skeleton templates for dynamic loading
    Used by page-skeleton-manager.js and offline-skeleton-v2.js
    """
    # Map template names to actual template paths
    template_mapping = {
        '_skeleton_post_feed.html': 'partials/_skeleton_post_feed.html',
        '_skeleton_profile.html': 'partials/_skeleton_profile.html',
        '_skeleton_groups_list.html': 'partials/_skeleton_groups_list.html',
        '_skeleton_group_detail.html': 'partials/_skeleton_group_detail.html',
        '_skeleton_notifications.html': 'partials/_skeleton_notifications.html',
        '_skeleton_post_detail.html': 'partials/_skeleton_post_detail.html',
        '_skeleton_course_detail.html': 'partials/_skeleton_course_detail.html',
        '_skeleton_messaging_list.html': 'partials/_skeleton_messaging_list.html',
        '_skeleton_messaging_detail.html': 'partials/_skeleton_messaging_detail.html',
        '_skeleton_search_results.html': 'partials/_skeleton_search_results.html',
    }
    
    template_path = template_mapping.get(template_name)
    if not template_path:
        return JsonResponse({'error': 'Skeleton template not found'}, status=404)
    
    return render(request, template_path)
