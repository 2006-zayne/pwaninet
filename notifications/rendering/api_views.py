"""
Profile-Driven Notification API Views
API endpoints that use the new profile-driven rendering system.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .profile_driven_renderer import profile_driven_renderer
from .profile_resolver import profile_resolver
from .payload_models import (
    NotificationPayload,
    NotificationIdentity,
    NotificationLifecycle,
    NotificationProfile,
    NotificationActor,
    NotificationMessage,
    NotificationComponents,
    NotificationPreview,
    NotificationMetadata,
    NotificationNavigation,
    NavigationTarget,
    NotificationPermissions,
    NotificationTimestamps,
    NotificationCapabilities,
    NotificationIntent,
    LifecycleState,
    MessageState,
    PreviewType,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_profiles_list(request):
    """
    List all available rendering profiles.
    
    Returns:
        JSON response with all registered profiles
    """
    profiles = profile_driven_renderer.list_available_profiles()
    return JsonResponse({
        'profiles': profiles,
        'count': len(profiles)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_profile_detail(request, notification_type):
    """
    Get profile information for a specific notification type.
    
    Args:
        notification_type: Type of notification
        
    Returns:
        JSON response with profile information
    """
    profile_info = profile_driven_renderer.get_profile_info(notification_type)
    is_known = profile_resolver.is_known_type(notification_type)
    
    return JsonResponse({
        'notification_type': notification_type,
        'is_known_type': is_known,
        'profile': profile_info
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def render_notification_payload(request):
    """
    Render a notification using the profile-driven pipeline.
    
    Expected JSON payload:
    {
        "type": "POST_LIKE",
        "intent": "activity",
        "actors": [...],
        "lifecycle": {...},
        ...
    }
    
    Returns:
        JSON response with complete rendering context
    """
    try:
        data = request.data
        
        # Build NotificationPayload from request data
        # This is a simplified example - in production, you'd have a proper adapter
        payload = _build_payload_from_request(data)
        
        # Render using profile-driven pipeline
        rendering_context = profile_driven_renderer.render(payload)
        
        return JsonResponse({
            'success': True,
            'rendering_context': rendering_context
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def _build_payload_from_request(data: dict) -> NotificationPayload:
    """
    Build a NotificationPayload from request data.
    This is a helper function - in production, use proper adapters.
    """
    # Extract actors
    actors = [
        NotificationActor(
            id=actor.get('id'),
            name=actor.get('name', 'Unknown'),
            username=actor.get('username', 'unknown'),
            avatar=actor.get('avatar'),
            verified=actor.get('verified', False)
        )
        for actor in data.get('actors', [])
    ]
    
    # Build payload
    return NotificationPayload(
        version=data.get('version', '1.0'),
        identity=NotificationIdentity(
            notification_id=data.get('notification_id', ''),
            recipient_id=data.get('recipient_id', 0),
            event_id=data.get('event_id', '')
        ),
        type=data.get('type', 'GENERIC'),
        intent=NotificationIntent(data.get('intent', 'activity')),
        lifecycle=NotificationLifecycle(
            state=LifecycleState(data.get('lifecycle_state', 'LIVE')),
            terminal=data.get('lifecycle_terminal', False)
        ),
        profile=NotificationProfile(
            id=data.get('type', 'GENERIC'),
            version='1.0'
        ),
        actors=actors,
        message=NotificationMessage(
            template=data.get('type', 'GENERIC'),
            state=MessageState(data.get('message_state', 'SINGLE')),
            variables=data.get('message_variables', {})
        ),
        components=NotificationComponents(
            context_header=data.get('components', {}).get('context_header', False),
            actor_stack=data.get('components', {}).get('actor_stack', True),
            content=data.get('components', {}).get('content', True),
            preview=data.get('components', {}).get('preview', False),
            metadata=data.get('components', {}).get('metadata', True),
            action_bar=data.get('components', {}).get('action_bar', False),
            status=data.get('components', {}).get('status', False)
        ),
        preview=NotificationPreview(
            enabled=data.get('preview', {}).get('enabled', False),
            type=PreviewType(data.get('preview', {}).get('type', 'NONE')),
            resource_id=data.get('preview', {}).get('resource_id')
        ),
        metadata=NotificationMetadata(
            read=data.get('metadata', {}).get('read', False),
            priority=data.get('metadata', {}).get('priority', 'NORMAL'),
            pinned=data.get('metadata', {}).get('pinned', False),
            aggregated=data.get('metadata', {}).get('aggregated', False)
        ),
        actions=[],  # Actions would be built from data
        navigation=NotificationNavigation(
            primary=NavigationTarget(
                target=data.get('navigation', {}).get('primary_target', ''),
                resource_id=data.get('navigation', {}).get('primary_resource_id')
            ) if data.get('navigation', {}).get('primary_target') else None
        ),
        permissions=NotificationPermissions(
            can_expand=data.get('permissions', {}).get('can_expand', True),
            can_reply=data.get('permissions', {}).get('can_reply', False),
            can_dismiss=data.get('permissions', {}).get('can_dismiss', True),
            can_execute_actions=data.get('permissions', {}).get('can_execute_actions', True)
        ),
        timestamps=NotificationTimestamps(
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at'),
            read_at=data.get('read_at'),
            completed_at=data.get('completed_at')
        ),
        raw_data=data.get('raw_data', {}),
        capabilities=NotificationCapabilities(
            expandable=data.get('capabilities', {}).get('expandable', False),
            aggregatable=data.get('capabilities', {}).get('aggregatable', False),
            actionable=data.get('capabilities', {}).get('actionable', False),
            previewable=data.get('capabilities', {}).get('previewable', False),
            navigable=data.get('capabilities', {}).get('navigable', True),
            dismissible=data.get('capabilities', {}).get('dismissible', True),
            shareable=data.get('capabilities', {}).get('shareable', False)
        )
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rendering_pipeline_status(request):
    """
    Get status of the rendering pipeline (cache stats, etc.).
    
    Returns:
        JSON response with pipeline status
    """
    cache_stats = profile_resolver.get_cache_stats()
    
    return JsonResponse({
        'profile_resolver': {
            'cache_stats': cache_stats
        },
        'message_engine': {
            'templates_count': len(message_engine._templates)
        }
    })
