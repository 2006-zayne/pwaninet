from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from users.models import User, Follow, DeviceAccount
from posts.models import Post, Like
from users.forms import PwaniSignupForm, ProfileUpdateForm, NotificationPreferencesForm
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from notifications.models import Notifications
from notifications.services.notification_service import invalidate_unread_count_cache, create_notification
from users.services.device_service import get_or_create_device_id, hash_device_id
from .serializers import (
    UserSerializer, UserPublicSerializer, FollowSerializer,
    DeviceAccountSerializer, UserUpdateSerializer, NotificationPreferencesSerializer
)
from .filters import UserFilter, FollowFilter


def register_view(request):
    if request.user.is_authenticated:
        return redirect('posts:home')
    if request.method == 'POST':
        form = PwaniSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('login')
    else:
        form = PwaniSignupForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile_view(request, username):
    from django.db.models import Count
    profile_user = get_object_or_404(
        User.objects.select_related('course__school', 'year'),
        username=username
    )
    profile_user = User.objects.filter(id=profile_user.id).select_related('course__school', 'year').annotate(
        followers_count=Count('follower_relationships', distinct=True),
        following_count=Count('following_relationships', distinct=True),
        total_likes=Count('posts__likes', distinct=True)
    ).first()
    posts = Post.objects.filter(author=profile_user).order_by('-created_at')
    is_following = Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    
    # Get shared posts for this profile user
    from posts.models import SharedPost
    from posts.services.share_service import get_user_received_shares
    shared_posts = get_user_received_shares(profile_user)
    
    # Count unseen shared posts for the badge
    unseen_shared_count = shared_posts.filter(is_viewed=False).count()
    
    # Determine if viewing own profile
    is_own_profile = request.user == profile_user
    
    # Get profile completion percentage for owner
    profile_completion = profile_user.profile_completion_percentage if is_own_profile else None
    
    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_following': is_following,
        'followers_count': profile_user.followers_count,
        'following_count': profile_user.following_count,
        'total_likes': profile_user.total_likes,
        'shared_posts': shared_posts,
        'unseen_shared_count': unseen_shared_count,
        'is_own_profile': is_own_profile,
        'profile_completion': profile_completion,
    })


@login_required
def mark_shared_viewed(request, username):
    """Mark all shared posts for the user as viewed"""
    from posts.models import SharedPost
    from django.http import HttpResponse
    from notifications.services.notification_service import invalidate_unread_count_cache
    from posts.services.share_service import get_user_received_shares
    from groups.models import Membership, MembershipStatus

    profile_user = get_object_or_404(User, username=username)

    # Only allow marking as viewed if viewing your own profile
    if request.user != profile_user:
        return HttpResponse('Unauthorized', status=403)

    # Get all received shares (direct + group shares)
    received_shares = get_user_received_shares(profile_user)

    # Mark all unseen received shares as viewed
    received_shares.filter(is_viewed=False).update(is_viewed=True)

    # Invalidate the unread count cache
    invalidate_unread_count_cache(profile_user.id)

    # Recalculate the unseen count to confirm it's 0
    shared_posts = get_user_received_shares(profile_user)
    unseen_count = shared_posts.filter(is_viewed=False).count()

    # Return updated tab HTML with updated count
    badge_html = f'<span class="badge bg-success rounded-pill ms-1">{unseen_count}</span>' if unseen_count > 0 else ''
    return HttpResponse(f'''
        <button class="nav-link" id="shared-tab" data-bs-toggle="tab" data-bs-target="#shared-content" type="button" role="tab"
                hx-post="/user/{username}/mark-shared-viewed/"
                hx-target="#shared-tab"
                hx-swap="outerHTML">
            Shared with {username}{badge_html}
        </button>
    ''')


@login_required
def update_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('users:profile', username=request.user.username)
            except Exception as e:
                messages.error(request, f'Error saving profile: {str(e)}')
                # Add debugging info
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Profile save error: {str(e)}", exc_info=True)
        else:
            # Add form errors to messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'users/update_profile.html', {'form': form})


@login_required
@transaction.atomic
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    
    is_ajax = request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if target == request.user:
        if is_ajax:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        return redirect('users:profile', username=username)

    follow_qs = Follow.objects.filter(follower=request.user, followed=target)
    if follow_qs.exists():
        follow_qs.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, followed=target)
        invalidate_unread_count_cache(target.id)
        is_following = True

    # Invalidate friend suggestions cache
    from users.services.friend_suggestion_service import invalidate_friend_suggestions_cache
    invalidate_friend_suggestions_cache(request.user.id)

    follower_count = target.follower_relationships.count()

    if request.headers.get('HX-Request'):
        # Return HTML partial based on which button triggered the request
        template = 'users/partials/follow_button_profile.html'
        if request.GET.get('source') == 'recruit':
            template = 'users/partials/follow_button_recruit.html'
        elif request.GET.get('source') == 'search':
            template = 'users/partials/follow_button_search.html'

        return render(request, template, {
            'profile_user': target,
            'recruit': target,
            'is_following': is_following,
            'follower_count': follower_count
        })

    if is_ajax:
        return JsonResponse({'is_following': is_following, 'follower_count': follower_count})

    return redirect('profile', username=username)


@login_required
def get_suggestions(request):
    from users.services.friend_suggestion_service import get_friend_suggestions_for_user
    suggestions = get_friend_suggestions_for_user(request.user, limit=5)
    return render(request, 'users/partials/suggestions.html', {'suggestions': suggestions})


@login_required
def notification_preferences_view(request):
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('users:notification_preferences')
    else:
        form = NotificationPreferencesForm(instance=request.user)
    return render(request, 'users/notification_preferences.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def mark_onboarding_complete(request):
    """
    Mark the current user's onboarding as completed.
    """
    request.user.has_completed_onboarding = True
    request.user.save()
    return JsonResponse({'status': 'success'})


@login_required
def switch_account_view(request, user_id):
    """
    Switch to a different account that is associated with the current device.
    """
    # Try to get device ID from headers first (HTMX requests)
    device_id = request.headers.get('X-Device-ID')
    
    # Fallback to query parameter (link clicks)
    if not device_id:
        device_id = request.GET.get('device_id')
    
    if not device_id:
        messages.error(request, 'Unable to identify device. Please refresh the page.')
        return redirect('posts:home')
    
    hashed_device_id = hash_device_id(device_id)
    
    # Verify the target account is associated with this device
    try:
        device_account = DeviceAccount.objects.get(
            user_id=user_id,
            device_id=hashed_device_id
        )
        target_user = device_account.user
    except DeviceAccount.DoesNotExist:
        messages.error(request, 'Account not found on this device.')
        return redirect('posts:home')
    
    # Logout current user
    logout(request)
    
    # Login as target user
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    
    # Update the device account record
    device_account.session_key = request.session.session_key
    device_account.save()
    
    messages.success(request, f'Switched to {target_user.username}')
    return redirect('posts:home')


@login_required
def get_device_accounts_view(request):
    """
    Get list of accounts associated with the current device.
    Returns JSON for the account switcher modal.
    """
    # Try to get device ID from headers first (HTMX requests)
    device_id = request.headers.get('X-Device-ID')
    
    if not device_id:
        return JsonResponse({'accounts': [], 'error': 'Device not identified'})
    
    hashed_device_id = hash_device_id(device_id)
    
    device_accounts = DeviceAccount.objects.filter(
        device_id=hashed_device_id
    ).select_related('user').order_by('-last_used')
    
    accounts_data = []
    for da in device_accounts:
        accounts_data.append({
            'id': da.user.id,
            'username': da.user.username,
            'full_name': str(da.user),
            'profile_pic': da.user.profile_pic.url if da.user.profile_pic else None,
            'last_used': da.last_used.isoformat(),
            'is_current': da.user.id == request.user.id
        })
    
    return JsonResponse({'accounts': accounts_data})


@login_required
def remove_account_from_device_view(request, user_id):
    """
    Remove an account from the current device's account list.
    Does not delete the user account, just removes the device association.
    """
    # Try to get device ID from headers first (HTMX requests)
    device_id = request.headers.get('X-Device-ID')
    
    # Fallback to query parameter (link clicks)
    if not device_id:
        device_id = request.GET.get('device_id')
    
    if not device_id:
        messages.error(request, 'Unable to identify device.')
        return redirect('posts:home')
    
    hashed_device_id = hash_device_id(device_id)
    
    # Prevent removing the current account
    if user_id == request.user.id:
        messages.error(request, 'Cannot remove the currently active account.')
        return redirect('posts:home')
    
    try:
        device_account = DeviceAccount.objects.get(
            user_id=user_id,
            device_id=hashed_device_id
        )
        device_account.delete()
        messages.success(request, 'Account removed from device.')
    except DeviceAccount.DoesNotExist:
        messages.error(request, 'Account not found on this device.')
    
    return redirect('posts:home')


@login_required
def view_profile_photo_fullscreen(request, username, photo_type):
    """
    View profile or cover photo in full screen mode.
    Only accessible if the viewer is following the profile user or if it's their own profile.
    """
    profile_user = get_object_or_404(User, username=username)
    
    # Check if user is allowed to view the photo
    is_own_profile = request.user == profile_user
    is_following = Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    
    if not is_own_profile and not is_following:
        messages.error(request, 'You need to follow this user to view their photos in full screen.')
        return redirect('users:profile', username=username)
    
    # Determine which photo to show
    if photo_type == 'profile':
        photo_url = profile_user.profile_pic.url
        photo_title = f"{profile_user.get_full_name}'s Profile Photo"
    elif photo_type == 'cover':
        if not profile_user.cover_photo:
            messages.error(request, 'This user does not have a cover photo.')
            return redirect('users:profile', username=username)
        photo_url = profile_user.cover_photo.url
        photo_title = f"{profile_user.get_full_name}'s Cover Photo"
    else:
        messages.error(request, 'Invalid photo type.')
        return redirect('users:profile', username=username)
    
    return render(request, 'users/profile_photo_fullscreen.html', {
        'profile_user': profile_user,
        'photo_url': photo_url,
        'photo_type': photo_type,
        'photo_title': photo_title,
        'is_own_profile': is_own_profile,
    })


# API ViewSets
class UserViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for User model.
    Provides list, create, retrieve, update, partial_update, delete actions.
    """
    queryset = User.objects.all().select_related('course__school', 'year')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'first_name', 'last_name', 'second_name']
    ordering_fields = ['username', 'date_joined', 'last_login']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UserPublicSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        summary="Get current user profile",
        description="Returns the authenticated user's profile information",
        responses={200: UserPublicSerializer}
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Follow or unfollow a user",
        description="Toggle follow status for a user",
        responses={200: {"status": "unfollowed"}, 201: {"status": "followed"}, 400: {"error": "message"}}
    )
    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        """Follow or unfollow a user"""
        target_user = self.get_object()
        if target_user == request.user:
            return Response(
                {'error': 'You cannot follow yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            followed=target_user
        )

        if not created:
            # Unfollow
            follow.delete()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)

        return Response({'status': 'followed'}, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get user's followers",
        description="Returns a paginated list of users following the specified user",
        responses={200: UserPublicSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def followers(self, request, pk=None):
        """Get list of followers for a user"""
        user = self.get_object()
        followers = User.objects.filter(follower_relationships__followed=user)
        page = self.paginate_queryset(followers)
        if page is not None:
            serializer = UserPublicSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserPublicSerializer(followers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get users followed by user",
        description="Returns a paginated list of users that the specified user is following",
        responses={200: UserPublicSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def following(self, request, pk=None):
        """Get list of users followed by a user"""
        user = self.get_object()
        following = User.objects.filter(follower_relationships__follower=user)
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = UserPublicSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserPublicSerializer(following, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Update notification preferences",
        description="Update the authenticated user's notification preferences",
        request=NotificationPreferencesSerializer,
        responses={200: NotificationPreferencesSerializer, 400: {"error": "message"}}
    )
    @action(detail=False, methods=['put', 'patch'])
    def update_preferences(self, request):
        """Update notification preferences"""
        serializer = NotificationPreferencesSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Update theme preference",
        description="Update the authenticated user's theme preference (light, dark, or system)",
        responses={200: {"theme_preference": "string"}, 400: {"error": "message"}}
    )
    @action(detail=False, methods=['patch'])
    def update_theme(self, request):
        """Update theme preference"""
        theme = request.data.get('theme_preference')
        if theme not in ['light', 'dark', 'system']:
            return Response(
                {'error': 'Invalid theme preference. Must be light, dark, or system.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.theme_preference = theme
        request.user.save()
        return Response({'theme_preference': theme})


class FollowViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Follow model.
    """
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = FollowFilter
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)


class DeviceAccountViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for DeviceAccount model.
    """
    queryset = DeviceAccount.objects.all()
    serializer_class = DeviceAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['last_used']
    ordering = ['-last_used']

    def get_queryset(self):
        return DeviceAccount.objects.filter(user=self.request.user)


@require_http_methods(["GET"])
def user_online_status_api(request, user_id):
    """
    API endpoint to check if a user is online.
    Returns JSON with is_online status using heartbeat-based presence tracking.
    """
    try:
        from messaging.presence import PresenceService
        
        # Check if user is online based on heartbeat freshness
        is_online = PresenceService.is_user_online(user_id)
        last_seen = PresenceService.get_last_seen(user_id)
        
        return JsonResponse({
            'is_online': is_online,
            'user_id': int(user_id),
            'last_seen': last_seen.isoformat() if last_seen else None
        })
    except Exception as e:
        return JsonResponse({
            'is_online': False,
            'user_id': int(user_id),
            'error': str(e)
        }, status=500)
