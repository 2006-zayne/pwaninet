from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.views.decorators.http import require_http_methods
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from users.models import User, Follow, DeviceAccount, Pinch, UserSession, Block, HiddenAuthor, PrivacyLevel
from posts.models import Post, Like
from users.forms import PwaniSignupForm, ProfileUpdateForm, NotificationPreferencesForm
from django.contrib import messages
from django.db import transaction
from notifications.models import Notifications
from notifications.services.notification_service import invalidate_unread_count_cache, create_notification
from users.services.device_service import get_or_create_device_id, hash_device_id
from users.services.email_verification_service import send_verification_email, verify_email_token
from .serializers import (
    UserSerializer, UserPublicSerializer, FollowSerializer, PinchSerializer,
    DeviceAccountSerializer, UserUpdateSerializer, NotificationPreferencesSerializer
)
from .filters import UserFilter, FollowFilter


def register_view(request):
    if request.user.is_authenticated:
        return redirect('posts:home')
    if request.method == 'POST':
        form = PwaniSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send verification email (non-blocking)
            send_verification_email(user)
            messages.success(request, 'Account created successfully. Please check your email for account verification instructions.')
            return redirect('login')
    else:
        form = PwaniSignupForm()
    return render(request, 'users/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    """
    Verify email address using token.
    This is a non-blocking verification - users can still login without verification.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and verify_email_token(user, token):
        messages.success(request, 'Your email has been verified successfully!')
        return redirect('login')
    else:
        messages.error(request, 'The verification link is invalid or has expired. Please request a new verification email.')
        return redirect('login')


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(
        User.objects.select_related('course__school', 'year'),
        username=username
    )
    
    # Fast individual count queries instead of a massive Cartesian product JOIN
    followers_count = profile_user.follower_relationships.count()
    following_count = profile_user.following_relationships.count()
    total_likes = Like.objects.filter(post__author=profile_user).count()
    pinches_sent_count = profile_user.pinches_sent.count()
    pinches_received_count = profile_user.pinches_received.count()

    # Pagination for posts - load first 10 posts
    from django.core.paginator import Paginator
    page = int(request.GET.get('page', 1))
    posts_per_page = 10
    
    posts_queryset = Post.objects.filter(author=profile_user).select_related('author', 'group', 'course', 'unit', 'repost_of').prefetch_related('likes', 'images', 'comments').order_by('-created_at')
    paginator = Paginator(posts_queryset, posts_per_page)
    posts_page = paginator.get_page(page)
    
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
    
    # Check if HTMX request for more posts
    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/post_cards_list.html', {
            'posts': posts_page,
            'has_more_posts': posts_page.has_next(),
            'profile_user': profile_user,
            'posts': posts_page,
        })
    
    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'posts': posts_page,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'total_likes': total_likes,
        'pinches_sent_count': pinches_sent_count,
        'pinches_received_count': pinches_received_count,
        'shared_posts': shared_posts,
        'unseen_shared_count': unseen_shared_count,
        'is_own_profile': is_own_profile,
        'profile_completion': profile_completion,
        'has_more_posts': posts_page.has_next(),
    })


@login_required
def profile_connections(request, username, list_type):
    """Return followers, following, pinches sent, or pinches received list for profile connections sheet."""
    from django.core.paginator import Paginator
    
    profile_user = get_object_or_404(User, username=username)
    page = int(request.GET.get('page', 1))
    page_size = 20

    if list_type == 'followers':
        follows = (
            Follow.objects.filter(followed=profile_user)
            .select_related('follower', 'follower__course', 'follower__year')
            .order_by('-created_at')
        )
        users = [f.follower for f in follows]
        title = 'Followers'
        empty_message = 'No followers yet.'
    elif list_type == 'following':
        follows = (
            Follow.objects.filter(follower=profile_user)
            .select_related('followed', 'followed__course', 'followed__year')
            .order_by('-created_at')
        )
        users = [f.followed for f in follows]
        title = 'Following'
        empty_message = 'Not following anyone yet.'
    elif list_type == 'pinches_sent':
        pinches = (
            Pinch.objects.filter(pinch_user=profile_user)
            .select_related('pinched_user', 'pinched_user__course', 'pinched_user__year')
            .order_by('-created_at')
        )
        users = [p.pinched_user for p in pinches]
        title = 'Pinches Sent'
        empty_message = 'No pinches sent yet.'
    elif list_type == 'pinches_received':
        pinches = (
            Pinch.objects.filter(pinched_user=profile_user)
            .select_related('pinch_user', 'pinch_user__course', 'pinch_user__year')
            .order_by('-created_at')
        )
        users = [p.pinch_user for p in pinches]
        title = 'Pinches Received'
        empty_message = 'No pinches received yet.'
    else:
        from django.http import HttpResponse
        return HttpResponse('Not found', status=404)

    # Paginate users
    paginator = Paginator(users, page_size)
    users_page = paginator.get_page(page)
    
    # Build next page URL if there are more pages
    next_url = None
    if users_page.has_next():
        next_url = f"{request.path}?page={users_page.next_page_number()}"

    return render(request, 'users/partials/connections_list.html', {
        'users': users_page,
        'title': title,
        'empty_message': empty_message,
        'profile_user': profile_user,
        'list_type': list_type,
        'has_more': users_page.has_next(),
        'next_url': next_url,
    })


@login_required
def people_search(request):
    """Search for users via HTMX for the people modal"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    import logging
    
    logger = logging.getLogger(__name__)
    
    search_query = request.GET.get('q', '').strip()
    connection_type = request.GET.get('connection_type', '')
    profile_username = request.GET.get('profile_username', '')
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    logger.info(f"people_search called - q={search_query}, connection_type={connection_type}, profile_username={profile_username}, page={page}")
    
    users = User.objects.none()
    list_type = 'all'
    empty_message = 'No users found.'
    empty_icon = 'search'
    
    # Get base users based on connection type
    if connection_type and profile_username:
        profile_user = get_object_or_404(User, username=profile_username)
        logger.info(f"Profile user found: {profile_user.username}")
        
        if connection_type == 'followers':
            follows = (
                Follow.objects.filter(followed=profile_user)
                .select_related('follower', 'follower__course', 'follower__year')
                .order_by('-created_at')
            )
            users = [f.follower for f in follows]
            list_type = 'followers'
            empty_message = 'No followers yet.'
            logger.info(f"Found {len(users)} followers")
        elif connection_type == 'following':
            follows = (
                Follow.objects.filter(follower=profile_user)
                .select_related('followed', 'followed__course', 'followed__year')
                .order_by('-created_at')
            )
            users = [f.followed for f in follows]
            list_type = 'following'
            empty_message = 'Not following anyone yet.'
            logger.info(f"Found {len(users)} following")
        elif connection_type == 'pinches_sent':
            pinches = (
                Pinch.objects.filter(pinch_user=profile_user)
                .select_related('pinched_user', 'pinched_user__course', 'pinched_user__year')
                .order_by('-created_at')
            )
            users = [p.pinched_user for p in pinches]
            list_type = 'pinches_sent'
            empty_message = 'No pinches sent yet.'
            logger.info(f"Found {len(users)} pinches sent")
        elif connection_type == 'pinches_received':
            pinches = (
                Pinch.objects.filter(pinched_user=profile_user)
                .select_related('pinch_user', 'pinch_user__course', 'pinch_user__year')
                .order_by('-created_at')
            )
            users = [p.pinch_user for p in pinches]
            list_type = 'pinches_received'
            empty_message = 'No pinches received yet.'
            logger.info(f"Found {len(users)} pinches received")
        
        # Apply search filter if provided
        if search_query and users:
            logger.info(f"Applying search filter '{search_query}' to {len(users)} users")
            users = [
                u for u in users
                if (search_query.lower() in u.username.lower() or
                    search_query.lower() in (u.first_name or '').lower() or
                    search_query.lower() in (u.last_name or '').lower())
            ]
            empty_message = f'No results for "{search_query}"'
            logger.info(f"After search filter: {len(users)} users")
    elif search_query:
        # Global search when no connection type
        users = (
            User.objects.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            .select_related('course', 'year')
            .exclude(id=request.user.id)
            .order_by('username')
        )
        list_type = 'search'
        empty_message = f'No results for "{search_query}"'
        logger.info(f"Global search found {len(users)} users")
    else:
        # Show suggested users when no search query and no connection type
        users = (
            User.objects
            .select_related('course', 'year')
            .exclude(id=request.user.id)
            .order_by('?')[:20]
        )
        list_type = 'suggested'
        empty_message = 'No users available'
        empty_icon = 'people'
        logger.info(f"Suggested users: {len(users)}")
    
    # Paginate
    paginator = Paginator(users, page_size)
    users_page = paginator.get_page(page)
    
    logger.info(f"After pagination: {len(users_page)} users on page {page}, has_more={users_page.has_next()}")
    
    # Build next page URL
    next_url = None
    if users_page.has_next():
        url_params = []
        if search_query:
            url_params.append(f"q={search_query}")
        if connection_type:
            url_params.append(f"connection_type={connection_type}")
        if profile_username:
            url_params.append(f"profile_username={profile_username}")
        url_params.append(f"page={users_page.next_page_number()}")
        next_url = f"?{'&'.join(url_params)}"
    
    logger.info(f"Rendering people_list.html with {len(users_page)} users")
    
    return render(request, 'users/partials/people_list.html', {
        'users': users_page,
        'list_type': list_type,
        'empty_message': empty_message,
        'empty_icon': empty_icon,
        'has_more': users_page.has_next(),
        'next_url': next_url,
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
@require_http_methods(["POST"])
@transaction.atomic
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    is_hx = request.headers.get('HX-Request')
    is_ajax = is_hx or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if target == request.user:
        if is_ajax:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        return redirect('users:profile', username=username)

    follow_qs = Follow.objects.filter(follower=request.user, followed=target)
    if follow_qs.exists():
        follow_qs.delete()
        is_following = False
    else:
        Follow.objects.get_or_create(follower=request.user, followed=target)
        invalidate_unread_count_cache(target.id)
        is_following = True

    from users.services.friend_suggestion_service import invalidate_friend_suggestions_cache
    invalidate_friend_suggestions_cache(request.user.id)

    follower_count = target.follower_relationships.count()

    if is_hx:
        template = 'users/partials/follow_button_profile.html'
        if request.GET.get('source') == 'recruit':
            template = 'users/partials/follow_button_recruit.html'
        elif request.GET.get('source') == 'search':
            template = 'users/partials/follow_button_search.html'

        return render(request, template, {
            'profile_user': target,
            'recruit': target,
            'is_following': is_following,
            'follower_count': follower_count,
        })

    if is_ajax:
        return JsonResponse({'is_following': is_following, 'follower_count': follower_count})

    return redirect('users:profile', username=username)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def toggle_pinch(request, username):
    """Toggle pinch on a user's profile"""
    from users.models import Pinch
    from django.utils import timezone
    from django.db.models import Count
    
    target = get_object_or_404(User, username=username)
    is_hx = request.headers.get('HX-Request')
    is_ajax = is_hx or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if target == request.user:
        if is_ajax:
            return JsonResponse({'error': 'Cannot pinch yourself'}, status=400)
        return redirect('users:profile', username=username)

    # Check if can pinch
    can_pinch, error_msg = Pinch.can_pinch(request.user, target)
    if not can_pinch:
        if is_ajax:
            return JsonResponse({'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('users:profile', username=username)

    # Create pinch
    pinch = Pinch.objects.create(pinch_user=request.user, pinched_user=target)
    
    # Invalidate cache
    invalidate_unread_count_cache(target.id)

    if is_hx:
        # Calculate updated pinch counts for the current user
        request_user = User.objects.filter(id=request.user.id).annotate(
            pinches_sent_count=Count('pinches_sent', distinct=True),
            pinches_received_count=Count('pinches_received', distinct=True)
        ).first()
        
        return render(request, 'users/partials/pinch_button.html', {
            'profile_user': target,
            'pinches_sent_count': request_user.pinches_sent_count,
            'pinches_received_count': request_user.pinches_received_count,
        })

    if is_ajax:
        return JsonResponse({'success': True, 'message': 'Pinched successfully'})

    messages.success(request, f'You pinched {target.username}!')
    return redirect('users:profile', username=username)


@login_required
def get_suggestions(request):
    from users.services.friend_suggestion_service import get_friend_suggestions_for_user
    suggestions = get_friend_suggestions_for_user(request.user, limit=5)
    return render(request, 'users/partials/suggestions.html', {'suggestions': suggestions})


@login_required
def settings_view(request):
    """Main settings landing page - navigation hub for all settings categories"""
    return render(request, 'users/settings/index.html')


@login_required
def settings_profile_view(request):
    """Profile settings page"""
    return render(request, 'users/settings/profile.html')


@login_required
def settings_appearance_view(request):
    """Appearance settings page"""
    return render(request, 'users/settings/appearance.html')


@login_required
def settings_notifications_view(request):
    """Notification settings page with form handling"""
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('users:settings_notifications')
    else:
        form = NotificationPreferencesForm(instance=request.user)
    return render(request, 'users/settings/notifications.html', {'form': form})


@login_required
def settings_privacy_view(request):
    """Privacy and security settings page"""
    return render(request, 'users/settings/privacy.html')


@login_required
def settings_storage_view(request):
    """Storage settings page"""
    return render(request, 'users/settings/storage.html')


@login_required
def settings_downloads_view(request):
    """Downloads manager page"""
    return render(request, 'users/settings/downloads.html')


@login_required
def settings_about_view(request):
    """About PwaniNet page with version information"""
    return render(request, 'users/settings/about.html')


@login_required
def settings_password_manager_view(request):
    """Password manager settings page"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'users/settings/password_manager.html')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'users/settings/password_manager.html')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'users/settings/password_manager.html')
        
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to keep user logged in
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('users:settings_password_manager')
    
    return render(request, 'users/settings/password_manager.html')


@login_required
def settings_active_devices_view(request):
    """Active devices management page"""
    from django.contrib.sessions.models import Session
    from user_agents import parse
    import re
    
    def parse_device_info(user_agent_string):
        """Parse detailed device information from user agent string"""
        user_agent = parse(user_agent_string)
        
        # Determine device type
        device_type = 'desktop'
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'
        
        # Try to extract device model from user agent string
        device_model = user_agent.device.family or 'Unknown Device'
        
        # Common Android device patterns
        android_patterns = [
            r'(SM-[A-Z0-9]+)',  # Samsung
            r'(Pixel [0-9]+)',  # Google Pixel
            r'(Redmi [A-Za-z0-9]+)',  # Xiaomi Redmi
            r'(POCO [A-Za-z0-9]+)',  # Xiaomi POCO
            r'(Tecno [A-Za-z0-9 ]+)',  # Tecno
            r'(Infinix [A-Za-z0-9 ]+)',  # Infinix
            r'(Itel [A-Za-z0-9 ]+)',  # Itel
            r'(Nokia [A-Za-z0-9]+)',  # Nokia
            r'(OnePlus [A-Za-z0-9]+)',  # OnePlus
            r'(OPPO [A-Za-z0-9]+)',  # OPPO
            r'(vivo [A-Za-z0-9]+)',  # Vivo
            r'(HUAWEI [A-Za-z0-9]+)',  # Huawei
            r'(Moto [A-Za-z0-9]+)',  # Motorola
            r'(LG-[A-Za-z0-9]+)',  # LG
            r'(Sony [A-Za-z0-9]+)',  # Sony
        ]
        
        for pattern in android_patterns:
            match = re.search(pattern, user_agent_string, re.IGNORECASE)
            if match:
                device_model = match.group(1)
                break
        
        # iPhone/iPad detection
        if 'iPhone' in user_agent_string:
            device_model = 'iPhone'
        elif 'iPad' in user_agent_string:
            device_model = 'iPad'
        
        # OS version formatting
        os_version = user_agent.os.version_string or ''
        if user_agent.os.family == 'Android' and os_version:
            # Clean up Android version (e.g., "12" instead of "12.0.0")
            os_version = os_version.split('.')[0]
        
        # Browser info
        browser_name = user_agent.browser.family or 'Unknown Browser'
        browser_version = user_agent.browser.version_string or ''
        if browser_version:
            browser_info = f"{browser_name} {browser_version.split('.')[0]}"
        else:
            browser_info = browser_name
        
        # OS info
        os_info = f"{user_agent.os.family}"
        if os_version:
            os_info += f" {os_version}"
        
        return {
            'device_type': device_type,
            'device_model': device_model,
            'browser': browser_info,
            'os': os_info,
            'is_mobile': user_agent.is_mobile,
            'is_tablet': user_agent.is_tablet,
            'is_pc': user_agent.is_pc,
        }
    
    # Get current session
    current_session_key = request.session.session_key
    current_session = None
    
    # Try to get or create UserSession for current session
    try:
        current_session = UserSession.objects.get(
            user=request.user,
            session_key=current_session_key
        )
        current_session.is_current = True
        current_session.last_activity = current_session.last_activity
    except UserSession.DoesNotExist:
        # Create session record
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        device_info = parse_device_info(user_agent_string)
        
        ip_address = request.META.get('REMOTE_ADDR')
        
        current_session = UserSession.objects.create(
            user=request.user,
            session_key=current_session_key,
            ip_address=ip_address,
            user_agent=user_agent_string,
            device_name=device_info['device_model'],
            browser=device_info['browser'],
            operating_system=device_info['os'],
            device_type=device_info['device_type'],
            is_current=True
        )
    
    # Get other sessions
    other_sessions = UserSession.objects.filter(
        user=request.user
    ).exclude(
        session_key=current_session_key
    ).order_by('-last_activity')
    
    # Parse device info for other sessions
    for session in other_sessions:
        if session.user_agent:
            device_info = parse_device_info(session.user_agent)
            session.device_type = device_info['device_type']
            session.device_model = device_info['device_model']
            session.browser = device_info['browser']
            session.os = device_info['os']
    
    # Parse device info for current session
    if current_session and current_session.user_agent:
        device_info = parse_device_info(current_session.user_agent)
        current_session.device_type = device_info['device_type']
        current_session.device_model = device_info['device_model']
        current_session.browser = device_info['browser']
        current_session.os = device_info['os']
    
    return render(request, 'users/settings/active_devices.html', {
        'current_session': current_session,
        'other_sessions': other_sessions
    })


@login_required
def settings_blocked_users_view(request):
    """Blocked users management page"""
    blocked_users = Block.objects.filter(
        blocker=request.user
    ).select_related('blocked').order_by('-created_at')
    
    return render(request, 'users/settings/blocked_users.html', {
        'blocked_users': blocked_users
    })


@login_required
def settings_profile_privacy_view(request):
    """Profile privacy settings page"""
    if request.method == 'POST':
        profile_privacy = request.POST.get('profile_privacy')
        
        if profile_privacy not in PrivacyLevel.values:
            messages.error(request, 'Invalid privacy level.')
            return redirect('users:settings_profile_privacy')
        
        request.user.profile_privacy = profile_privacy
        request.user.save()
        
        messages.success(request, 'Profile privacy updated successfully.')
        return redirect('users:settings_profile_privacy')
    
    privacy_levels = PrivacyLevel.choices
    return render(request, 'users/settings/profile_privacy.html', {
        'privacy_levels': privacy_levels
    })


@login_required
def settings_post_privacy_view(request):
    """Post privacy settings page"""
    if request.method == 'POST':
        post_privacy = request.POST.get('post_privacy')
        
        if post_privacy not in PrivacyLevel.values:
            messages.error(request, 'Invalid privacy level.')
            return redirect('users:settings_post_privacy')
        
        request.user.post_privacy = post_privacy
        request.user.save()
        
        messages.success(request, 'Post privacy updated successfully.')
        return redirect('users:settings_post_privacy')
    
    privacy_levels = PrivacyLevel.choices
    return render(request, 'users/settings/post_privacy.html', {
        'privacy_levels': privacy_levels
    })


@login_required
def settings_hidden_authors_view(request):
    """Hidden authors management page"""
    hidden_authors = HiddenAuthor.objects.filter(
        hider=request.user
    ).select_related('hidden_author').order_by('-created_at')
    
    return render(request, 'users/settings/hidden_authors.html', {
        'hidden_authors': hidden_authors
    })


@login_required
def notification_preferences_view(request):
    """Legacy view - redirects to new notifications settings page"""
    return redirect('users:settings_notifications')


@login_required
@require_http_methods(["POST"])
def api_sign_out_session(request, session_id):
    """Sign out a specific session (API endpoint for HTMX)"""
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
        
        # Prevent signing out current session
        if session.session_key == request.session.session_key:
            return JsonResponse({'error': 'Cannot sign out current session'}, status=400)
        
        # Delete the Django session
        from django.contrib.sessions.models import Session
        try:
            django_session = Session.objects.get(session_key=session.session_key)
            django_session.delete()
        except Session.DoesNotExist:
            pass
        
        # Delete our UserSession record
        session.delete()
        
        return HttpResponse('')  # HTMX will remove the element
    except UserSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_sign_out_all_sessions(request):
    """Sign out all other sessions (API endpoint for HTMX)"""
    current_session_key = request.session.session_key
    
    # Delete all other sessions
    other_sessions = UserSession.objects.filter(
        user=request.user
    ).exclude(
        session_key=current_session_key
    )
    
    from django.contrib.sessions.models import Session
    for session in other_sessions:
        try:
            django_session = Session.objects.get(session_key=session.session_key)
            django_session.delete()
        except Session.DoesNotExist:
            pass
        session.delete()
    
    messages.success(request, 'All other devices have been signed out.')
    return redirect('users:settings_active_devices')


@login_required
@require_http_methods(["POST"])
def api_unblock_user(request, user_id):
    """Unblock a user (API endpoint for HTMX)"""
    try:
        blocked_user = User.objects.get(id=user_id)
        block = Block.objects.get(blocker=request.user, blocked=blocked_user)
        block.delete()
        
        return HttpResponse('')  # HTMX will remove the element
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Block.DoesNotExist:
        return JsonResponse({'error': 'Block not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_show_hidden_author(request, user_id):
    """Remove author from hidden list (API endpoint for HTMX)"""
    try:
        hidden_author = User.objects.get(id=user_id)
        hidden = HiddenAuthor.objects.get(hider=request.user, hidden_author=hidden_author)
        hidden.delete()
        
        return HttpResponse('')  # HTMX will remove the element
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except HiddenAuthor.DoesNotExist:
        return JsonResponse({'error': 'Hidden author not found'}, status=404)


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

    @extend_schema(
        summary="Update appearance preferences",
        description="Update the authenticated user's appearance preferences (theme, font_size, language)",
        responses={200: {"theme_preference": "string", "font_size_preference": "string", "language_preference": "string"}, 400: {"error": "message"}}
    )
    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        """Update appearance preferences"""
        data = request.data
        updated_fields = {}

        # Update theme preference if provided
        if 'theme_preference' in data:
            theme = data['theme_preference']
            if theme not in ['light', 'dark', 'system']:
                return Response(
                    {'error': 'Invalid theme preference. Must be light, dark, or system.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.theme_preference = theme
            updated_fields['theme_preference'] = theme

        # Update font size preference if provided
        if 'font_size_preference' in data:
            font_size = data['font_size_preference']
            if font_size not in ['tiny', 'small', 'medium', 'large']:
                return Response(
                    {'error': 'Invalid font size preference. Must be tiny, small, medium, or large.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.font_size_preference = font_size
            updated_fields['font_size_preference'] = font_size

        # Update language preference if provided
        if 'language_preference' in data:
            language = data['language_preference']
            if language not in ['en', 'sw']:
                return Response(
                    {'error': 'Invalid language preference. Must be en or sw.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.language_preference = language
            updated_fields['language_preference'] = language

        request.user.save()
        return Response(updated_fields)


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


class PinchViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Pinch model.
    """
    queryset = Pinch.objects.all().select_related('pinch_user', 'pinched_user')
    serializer_class = PinchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Pinch.objects.filter(pinch_user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(pinch_user=self.request.user)


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
    FROZEN FOR MVP - Messaging presence disabled
    """
    try:
        # Messaging presence - FROZEN FOR MVP
        # from messaging.presence import PresenceService
        
        # Check if user is online based on heartbeat freshness - FROZEN FOR MVP
        # is_online = PresenceService.is_user_online(user_id)
        # last_seen = PresenceService.get_last_seen(user_id)
        
        # Fallback to basic User model is_online field
        from users.models import User
        user = User.objects.get(id=user_id)
        
        return JsonResponse({
            'is_online': user.is_online,
            'user_id': int(user_id),
            'last_seen': None  # Presence tracking disabled
        })
    except Exception as e:
        return JsonResponse({
            'is_online': False,
            'user_id': int(user_id),
            'error': str(e)
        }, status=500)
