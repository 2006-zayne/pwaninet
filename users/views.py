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
from django.db.models import Q
from users.models import User, Follow, DeviceAccount, Pinch, UserSession, Block, HiddenAuthor, PrivacyLevel
from posts.models import Post, Like
from users.forms import PwaniSignupForm, ProfileUpdateForm
from django.contrib import messages
from django.db import transaction
from notifications.models import NotificationObject
from notifications.services.notification_service import invalidate_unread_count_cache
from users.services.device_service import get_or_create_device_id, hash_device_id
from users.services.email_verification_service import send_verification_email, verify_email_token
from pwaninet.utils.htmx import htmx_location_response
from .serializers import (
    UserSerializer, UserPublicSerializer, FollowSerializer, PinchSerializer,
    DeviceAccountSerializer, UserUpdateSerializer, NotificationPreferencesSerializer
)
import logging
from django.contrib.auth.views import LoginView
from .filters import UserFilter, FollowFilter

logger = logging.getLogger('users.auth')


def get_client_ip(request):
    """Safely extract the client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def register_view(request):
    """
    Handle user registration with robust validation, detailed logging,
    and clear user-facing error feedback.
    """
    if request.user.is_authenticated:
        return redirect('posts:home')

    if request.method == 'POST':
        ip = get_client_ip(request)
        submitted_username = request.POST.get('username', '').strip()
        msg_attempt = f"[AUTH-REGISTER] Registration attempt received from IP={ip} for username='{submitted_username}'"
        print(msg_attempt, flush=True)
        logger.info(msg_attempt)

        form = PwaniSignupForm(request.POST)
        try:
            if form.is_valid():
                user = form.save()
                msg_success = f"[AUTH-REGISTER] SUCCESS: User created. id={user.id}, username='{user.username}', IP={ip}"
                print(msg_success, flush=True)
                logger.info(msg_success)
                request.session['registered_username'] = user.username
                messages.success(request, f"Welcome @{user.username}! Your account has been created successfully. Please log in.")
                return redirect('login')
            else:
                msg_warn = f"[AUTH-REGISTER] Validation failed for username='{submitted_username}', IP={ip}. Errors: {form.errors.as_json()}"
                print(msg_warn, flush=True)
                logger.warning(msg_warn)
                messages.error(request, "Please correct the errors highlighted below.")
        except Exception as e:
            msg_err = f"[AUTH-REGISTER] Unexpected exception for username='{submitted_username}': {e}"
            print(msg_err, flush=True)
            logger.error(msg_err, exc_info=True)
            messages.error(request, "An unexpected server error occurred during account creation. Please try again.")
    else:
        form = PwaniSignupForm()

    return render(request, 'users/register.html', {'form': form})


class PwaniLoginView(LoginView):
    """
    Custom LoginView providing:
    1. Structured logging of authentication attempts and failures.
    2. Intelligent diagnostic error messages to help users (e.g. distinguishing
       non-existent accounts from wrong passwords).
    3. Seamless redirection and session cleanup for newly registered users.
    """
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('posts:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        ip = get_client_ip(self.request)
        msg = f"[AUTH-LOGIN] SUCCESS: User '{user.username}' (id={user.id}) authenticated from IP={ip}"
        print(msg, flush=True)
        logger.info(msg)
        # Clean up transient registered_username session key
        self.request.session.pop('registered_username', None)
        return super().form_valid(form)

    def form_invalid(self, form):
        username = self.request.POST.get('username', '').strip()
        ip = get_client_ip(self.request)
        msg_fail = f"[AUTH-LOGIN] FAILED: Login failed for username='{username}' from IP={ip}"
        print(msg_fail, flush=True)
        logger.warning(msg_fail)

        context_extra = {
            'attempted_username': username,
        }

        # Check DB to distinguish whether user exists or not
        user_match = User.objects.filter(username__iexact=username).first()
        if not user_match and '@' in username:
            user_match = User.objects.filter(email__iexact=username).first()

        if user_match is None:
            msg_diag = f"[AUTH-LOGIN] Diagnostic: No account found for username='{username}' in DB."
            print(msg_diag, flush=True)
            logger.warning(msg_diag)
            context_extra['login_error_type'] = 'account_not_found'
            context_extra['login_error_message'] = (
                f"No account exists with the username '{username}'. "
                "If you haven't created an account yet, please sign up."
            )
        elif not user_match.is_active:
            msg_diag = f"[AUTH-LOGIN] Diagnostic: User '{user_match.username}' is inactive."
            print(msg_diag, flush=True)
            logger.warning(msg_diag)
            context_extra['login_error_type'] = 'account_inactive'
            context_extra['login_error_message'] = (
                f"The account '{user_match.username}' has been deactivated. Please contact support."
            )
        else:
            msg_diag = f"[AUTH-LOGIN] Diagnostic: Incorrect password for existing user '{user_match.username}'."
            print(msg_diag, flush=True)
            logger.warning(msg_diag)
            context_extra['login_error_type'] = 'wrong_password'
            context_extra['login_error_message'] = (
                f"Incorrect password for '{user_match.username}'. Please check your password or reset it below."
            )

        return self.render_to_response(self.get_context_data(form=form, **context_extra))


def load_academic_levels(request):
    """HTMX endpoint to load academic levels for a programme."""
    programme_id = request.GET.get('programme_id')
    from documents.academic.models import AcademicLevel
    levels = AcademicLevel.objects.filter(is_active=True).order_by('level')
    return render(request, 'users/partials/academic_level_options.html', {'levels': levels})


def load_academic_years(request):
    """HTMX endpoint to load academic years."""
    from documents.academic.models import AcademicYear
    years = AcademicYear.objects.all().order_by('-code')
    return render(request, 'users/partials/academic_year_options.html', {'years': years})


def load_semesters(request):
    """HTMX endpoint to load semesters for an academic year."""
    academic_year_id = request.GET.get('academic_year_id')
    from documents.academic.models import Semester
    if academic_year_id:
        semesters = Semester.objects.filter(academic_year_id=academic_year_id).order_by('number')
    else:
        semesters = Semester.objects.none()
    return render(request, 'users/partials/semester_options.html', {'semesters': semesters})


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
        User.objects.select_related(
            'programme__department__school',
            'academic_level',
            'academic_year',
            'semester',
            'course__school',
            'year'
        ),
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

    # Filter posts: show regular posts and group posts only if viewing user is a member of the group
    from groups.models import Membership, MembershipStatus
    viewer_group_ids = list(Membership.objects.filter(
        user=request.user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True))

    posts_queryset = Post.objects.filter(
        author=profile_user
    ).filter(
        Q(group__isnull=True) | Q(group_id__in=viewer_group_ids)
    ).select_related('author', 'group', 'course', 'unit', 'repost_of').prefetch_related('likes', 'images', 'comments').order_by('-created_at')
    paginator = Paginator(posts_queryset, posts_per_page)
    posts_page = paginator.get_page(page)

    # Get liked post IDs for the current user
    liked_post_ids = set()
    if request.user.is_authenticated:
        for pid, sid in Like.objects.filter(user=request.user, post__in=posts_page).values_list('post_id', 'post__share_id'):
            liked_post_ids.add(pid)
            liked_post_ids.add(sid)
            liked_post_ids.add(str(sid))

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

    # HTMX Navigation Request: Return full navigation partial for page navigation
    # Distinguished from infinite scroll (has page parameter)
    if request.headers.get('HX-Request') and not request.GET.get('page'):
        context = {
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
            'liked_post_ids': liked_post_ids,
        }
        return render(request, 'users/partials/profile_navigation_partial.html', context)

    # For HTMX infinite scroll: render only the posts partial
    if request.headers.get('HX-Request') and page:
        return render(request, 'posts/partials/post_cards_list.html', {
            'posts': posts_page,
            'has_more_posts': posts_page.has_next(),
            'profile_user': profile_user,
            'posts': posts_page,
            'liked_post_ids': liked_post_ids,
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
        'liked_post_ids': liked_post_ids,
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
    """Search for users via HTMX for the people modal powered by UnifiedSearchService."""
    search_query = request.GET.get('q', '').strip()
    connection_type = request.GET.get('connection_type', '')
    profile_username = request.GET.get('profile_username', '')
    page = int(request.GET.get('page', 1))
    page_size = 20

    from search.services.unified_search_service import UnifiedSearchService
    search_service = UnifiedSearchService()

    users_page, list_type, empty_message, empty_icon, has_more, next_url = search_service.search_people_models(
        query=search_query,
        user=request.user,
        connection_type=connection_type,
        profile_username=profile_username,
        page=page,
        page_size=page_size,
    )

    return render(request, 'users/partials/people_list.html', {
        'users': users_page,
        'list_type': list_type,
        'empty_message': empty_message,
        'empty_icon': empty_icon,
        'has_more': has_more,
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
    is_htmx = bool(request.headers.get('HX-Request'))
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Profile updated successfully.')
                if is_htmx:
                    from django.urls import reverse
                    return htmx_location_response(reverse('users:profile', kwargs={'username': request.user.username}))
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

    template = 'users/partials/update_profile_navigation_partial.html' if is_htmx else 'users/update_profile.html'
    return render(request, template, {'form': form})


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
        elif request.GET.get('source') == 'onboarding':
            template = 'users/partials/follow_button_onboarding.html'

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
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/index_content.html'
        })
    return render(request, 'users/settings/index.html')


@login_required
def settings_profile_view(request):
    """Profile settings page"""
    is_htmx = bool(request.headers.get('HX-Request'))
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Profile updated successfully.')
                if is_htmx:
                    from django.urls import reverse
                    return htmx_location_response(reverse('users:settings_profile'))
                return redirect('users:settings_profile')
            except Exception as e:
                messages.error(request, f'Error saving profile: {str(e)}')
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Profile save error: {str(e)}", exc_info=True)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ProfileUpdateForm(instance=request.user)

    if is_htmx:
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/profile_content.html',
            'form': form,
        })
    return render(request, 'users/settings/profile.html', {'form': form})


@login_required
def settings_appearance_view(request):
    """Appearance settings page"""
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/appearance_content.html'
        })
    return render(request, 'users/settings/appearance.html')



@login_required
def settings_privacy_view(request):
    """Privacy and security settings page"""
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/privacy_content.html'
        })
    return render(request, 'users/settings/privacy.html')


def settings_storage_view(request):
    """Storage settings page - seamlessly renders unified downloaded media page"""
    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/offline_media_viewer_content.html')
    return redirect('posts:offline_media_viewer')


def settings_downloads_view(request):
    """Downloads manager page - seamlessly renders unified downloaded media page"""
    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/offline_media_viewer_content.html')
    return redirect('posts:offline_media_viewer')


@login_required
def settings_about_view(request):
    """About PwaniNet page with version information"""
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/about_content.html'
        })
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
            if request.headers.get('HX-Request'):
                return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                    'settings_content_partial': 'users/settings/partials/password_content.html'
                })
            return render(request, 'users/settings/password_manager.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            if request.headers.get('HX-Request'):
                return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                    'settings_content_partial': 'users/settings/partials/password_content.html'
                })
            return render(request, 'users/settings/password_manager.html')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            if request.headers.get('HX-Request'):
                return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                    'settings_content_partial': 'users/settings/partials/password_content.html'
                })
            return render(request, 'users/settings/password_manager.html')

        request.user.set_password(new_password)
        request.user.save()

        # Update session to keep user logged in
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password changed successfully.')
        if request.headers.get('HX-Request'):
            return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                'settings_content_partial': 'users/settings/partials/password_content.html'
            })
        return redirect('users:settings_password_manager')

    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/password_content.html'
        })
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

    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/active_devices_content.html',
            'current_session': current_session,
            'other_sessions': other_sessions
        })

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

    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/blocked_content.html',
            'blocked_users': blocked_users
        })

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
        else:
            request.user.profile_privacy = profile_privacy
            request.user.save()
            messages.success(request, 'Profile privacy updated successfully.')

        if request.headers.get('HX-Request'):
            return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                'settings_content_partial': 'users/settings/partials/profile_privacy_content.html',
                'privacy_levels': PrivacyLevel.choices
            })
        return redirect('users:settings_profile_privacy')

    privacy_levels = PrivacyLevel.choices
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/profile_privacy_content.html',
            'privacy_levels': privacy_levels
        })
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
        else:
            request.user.post_privacy = post_privacy
            request.user.save()
            messages.success(request, 'Post privacy updated successfully.')

        if request.headers.get('HX-Request'):
            return render(request, 'users/settings/partials/settings_navigation_partial.html', {
                'settings_content_partial': 'users/settings/partials/post_privacy_content.html',
                'privacy_levels': PrivacyLevel.choices
            })
        return redirect('users:settings_post_privacy')

    privacy_levels = PrivacyLevel.choices
    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/post_privacy_content.html',
            'privacy_levels': privacy_levels
        })
    return render(request, 'users/settings/post_privacy.html', {
        'privacy_levels': privacy_levels
    })


@login_required
def settings_hidden_authors_view(request):
    """Hidden authors management page"""
    hidden_authors = HiddenAuthor.objects.filter(
        hider=request.user
    ).select_related('hidden_author').order_by('-created_at')

    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/hidden_content.html',
            'hidden_authors': hidden_authors
        })

    return render(request, 'users/settings/hidden_authors.html', {
        'hidden_authors': hidden_authors
    })


@login_required
def settings_notifications_view(request):
    """Notification preferences settings page"""
    from notifications.services.preference_service import NotificationPreferenceService
    from notifications.events import EventTypes
    from datetime import time
    from django.contrib import messages

    event_type_mapping = {
        'POSTS_POST_LIKED': EventTypes.POSTS_POST_LIKED.value,
        'POSTS_COMMENT_CREATED': EventTypes.POSTS_COMMENT_CREATED.value,
        'POSTS_COMMENT_REPLY_CREATED': EventTypes.POSTS_COMMENT_REPLY_CREATED.value,
        'POSTS_COMMENT_REPLIED': EventTypes.POSTS_COMMENT_REPLIED.value,
        'POSTS_POST_SHARED': EventTypes.POSTS_POST_SHARED.value,
        'POSTS_POST_REPOSTED': EventTypes.POSTS_POST_REPOSTED.value,
        'POSTS_POST_SHARED_TO_GROUP': EventTypes.POSTS_POST_SHARED_TO_GROUP.value,
        'USERS_USER_FOLLOWED': EventTypes.USERS_USER_FOLLOWED.value,
        'USERS_USER_PINCHED': EventTypes.USERS_USER_PINCHED.value,
        'GROUPS_MEMBER_INVITED': EventTypes.GROUPS_MEMBER_INVITED.value,
        'GROUPS_MEMBER_REQUESTED': EventTypes.GROUPS_MEMBER_REQUESTED.value,
        'GROUPS_MEMBER_APPROVED': EventTypes.GROUPS_MEMBER_APPROVED.value,
        'GROUPS_MEMBER_REJECTED': EventTypes.GROUPS_MEMBER_REJECTED.value,
        'DOCUMENTS_DOCUMENT_UPLOADED': EventTypes.DOCUMENTS_DOCUMENT_UPLOADED.value,
        'DOCUMENTS_DOCUMENT_DOWNLOADED': EventTypes.DOCUMENTS_DOCUMENT_DOWNLOADED.value,
        'DOCUMENTS_DOCUMENT_BOOKMARKED': EventTypes.DOCUMENTS_DOCUMENT_BOOKMARKED.value,
        'DOCUMENTS_DOCUMENT_RATED': EventTypes.DOCUMENTS_DOCUMENT_RATED.value,
        'MESSAGING_MESSAGE_SENT': EventTypes.MESSAGING_MESSAGE_SENT.value,
        'MESSAGING_CONVERSATION_CREATED': EventTypes.MESSAGING_CONVERSATION_CREATED.value,
        'MESSAGING_CONVERSATION_MEMBER_ADDED': EventTypes.MESSAGING_CONVERSATION_MEMBER_ADDED.value,
        'COURSES_ASSIGNMENT_PUBLISHED': EventTypes.COURSES_ASSIGNMENT_PUBLISHED.value,
    }

    preferences = NotificationPreferenceService.get_or_create_preferences(request.user)

    # Handle form submission
    if request.method == 'POST':
        # Update global preferences
        preferences.email_enabled = request.POST.get('email_enabled') in ('on', 'true', '1')
        preferences.email_digest = request.POST.get('email_digest') in ('on', 'true', '1')
        preferences.push_enabled = request.POST.get('push_enabled') in ('on', 'true', '1')
        preferences.push_sound = request.POST.get('push_sound') in ('on', 'true', '1')
        preferences.in_app_enabled = request.POST.get('in_app_enabled') in ('on', 'true', '1')
        preferences.in_app_toast_enabled = request.POST.get('in_app_toast_enabled') in ('on', 'true', '1')

        # Update quiet hours
        preferences.quiet_hours_enabled = request.POST.get('quiet_hours_enabled') in ('on', 'true', '1')
        quiet_hours_start = request.POST.get('quiet_hours_start')
        quiet_hours_end = request.POST.get('quiet_hours_end')

        if quiet_hours_start:
            try:
                preferences.quiet_hours_start = time.fromisoformat(quiet_hours_start)
            except (ValueError, TypeError):
                preferences.quiet_hours_start = None
        else:
            preferences.quiet_hours_start = None

        if quiet_hours_end:
            try:
                preferences.quiet_hours_end = time.fromisoformat(quiet_hours_end)
            except (ValueError, TypeError):
                preferences.quiet_hours_end = None
        else:
            preferences.quiet_hours_end = None

        # Update type preferences
        if not isinstance(preferences.type_preferences, dict):
            preferences.type_preferences = {}

        for field_name, event_type in event_type_mapping.items():
            email_val = request.POST.get(f'type_{field_name}_email') in ('on', 'true', '1')
            push_val = request.POST.get(f'type_{field_name}_push') in ('on', 'true', '1')
            in_app_val = request.POST.get(f'type_{field_name}_in_app') in ('on', 'true', '1')
            preferences.type_preferences[event_type] = {
                'email': email_val,
                'push': push_val,
                'in_app': in_app_val,
            }

        preferences.save()

        # Update cache on user instance if present
        if hasattr(request.user, '_state') and hasattr(request.user._state, 'fields_cache'):
            request.user._state.fields_cache['notification_preferences'] = preferences

        messages.success(request, 'Notification preferences updated successfully.')

        if not request.headers.get('HX-Request'):
            return redirect('users:settings_notifications')

    # Ensure type_preferences is a dictionary
    if not isinstance(preferences.type_preferences, dict):
        preferences.type_preferences = {}

    # Check if event types are populated; if not, merge default type preferences
    has_event_types = any(k in preferences.type_preferences for k in event_type_mapping.values())
    if not has_event_types:
        defaults = NotificationPreferenceService.get_default_type_preferences()
        for k, v in defaults.items():
            if k not in preferences.type_preferences:
                preferences.type_preferences[k] = v
        preferences.save()

    # Create a mapping for template access (dot keys -> underscore keys)
    template_preferences = preferences
    template_preferences.type_preferences_template = {}
    for underscore_key, dot_key in event_type_mapping.items():
        if dot_key in preferences.type_preferences and isinstance(preferences.type_preferences[dot_key], dict):
            template_preferences.type_preferences_template[underscore_key] = preferences.type_preferences[dot_key]
        else:
            template_preferences.type_preferences_template[underscore_key] = {
                'email': preferences.email_enabled,
                'push': preferences.push_enabled,
                'in_app': preferences.in_app_enabled,
            }

    if request.headers.get('HX-Request'):
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/notification_preferences_content.html',
            'preferences': template_preferences
        })

    return render(request, 'users/settings/notifications.html', {
        'preferences': template_preferences
    })


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
    if request.headers.get('HX-Request'):
        current_session = UserSession.objects.filter(user=request.user, session_key=current_session_key).first()
        return render(request, 'users/settings/partials/settings_navigation_partial.html', {
            'settings_content_partial': 'users/settings/partials/active_devices_content.html',
            'current_session': current_session,
            'other_sessions': []
        })
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
    request.user.save(update_fields=['has_completed_onboarding'])
    return JsonResponse({'status': 'success'})


@login_required
def onboarding_wizard_view(request):
    """
    Dedicated pre-feed onboarding view.
    Presents classmates to follow and groups to join before reaching the home feed.
    """
    from recommendations.services.engine import UnifiedRecommendationEngine
    from groups.models import Membership, MembershipStatus

    # If already completed and not explicitly restarting, go straight to feed
    if request.user.has_completed_onboarding and not request.GET.get('restart'):
        return redirect('posts:home')

    data = UnifiedRecommendationEngine.get_onboarding_data(request.user)

    following_ids = set(
        Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True)
    )
    joined_group_ids = set(
        Membership.objects.filter(
            user=request.user,
            status__in=[MembershipStatus.APPROVED, MembershipStatus.PENDING]
        ).values_list('group_id', flat=True)
    )

    context = {
        'classmates': data['classmates'],
        'recommended_groups': data['recommended_groups'],
        'official_groups': data['official_groups'],
        'following_ids': following_ids,
        'joined_group_ids': joined_group_ids,
    }
    return render(request, 'users/onboarding/wizard.html', context)


@login_required
@require_http_methods(["POST"])
def batch_follow_view(request):
    """
    1-click Follow All Suggested classmates during onboarding.
    """
    import json
    from recommendations.services.engine import UnifiedRecommendationEngine

    user_ids = request.POST.getlist('user_ids')
    if not user_ids and request.body:
        try:
            body = json.loads(request.body)
            user_ids = body.get('user_ids', [])
        except Exception:
            pass

    if not user_ids:
        # Default: follow all top suggestions
        suggestions = UnifiedRecommendationEngine.get_recommended_users(
            request.user, limit=12, use_cache=False, context='onboarding'
        )
        user_ids = [u.id for u in suggestions]

    user_ids = [int(uid) for uid in user_ids if str(uid).isdigit() and int(uid) != request.user.id]

    new_follows = []
    for uid in user_ids:
        follow, created = Follow.objects.get_or_create(follower=request.user, followed_id=uid)
        if created:
            new_follows.append(follow)
            invalidate_unread_count_cache(uid)

    UnifiedRecommendationEngine.invalidate_all_user_caches(request.user.id)

    if request.headers.get('HX-Request'):
        data = UnifiedRecommendationEngine.get_onboarding_data(request.user)
        following_ids = set(
            Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True)
        )
        return render(request, 'users/onboarding/partials/step_classmates.html', {
            'classmates': data['classmates'],
            'following_ids': following_ids,
            'all_followed': True,
        })

    return JsonResponse({'status': 'success', 'followed_count': len(new_follows)})


@login_required
@require_http_methods(["GET", "POST"])
def complete_onboarding_view(request):
    """
    Mark onboarding as complete, set session flag for feed welcome banner,
    and redirect user to their populated home feed.
    """
    from recommendations.services.engine import UnifiedRecommendationEngine
    from django.core.cache import cache
    request.user.has_completed_onboarding = True
    request.user.save(update_fields=['has_completed_onboarding'])

    UnifiedRecommendationEngine.invalidate_all_user_caches(request.user.id)
    cache.delete(f'feed:user_suggestions:{request.user.id}')
    cache.delete(f'feed:following_ids:{request.user.id}')
    cache.delete(f'feed:suggested_groups:{request.user.id}')

    request.session['just_onboarded'] = True
    messages.success(request, "Welcome to PwaniNet! You're connected with your campus network.")
    return redirect('posts:home')


@login_required
@require_http_methods(["POST"])
def dismiss_welcome_banner_view(request):
    """Dismiss the feed welcome banner for the current session."""
    if 'just_onboarded' in request.session:
        del request.session['just_onboarded']
    return JsonResponse({'status': 'dismissed'})


@login_required
def switch_account_view(request, user_id):
    """
    Switch to a different account that is associated with the current device.
    """
    from django.urls import reverse
    from django.utils.http import url_has_allowed_host_and_scheme

    # Try to get device ID from attribute, headers, POST, or query params
    device_id = getattr(request, 'device_id', None)
    if not device_id:
        device_id = request.headers.get('X-Device-ID')
    if not device_id and hasattr(request, 'POST'):
        device_id = request.POST.get('device_id')
    if not device_id and hasattr(request, 'GET'):
        device_id = request.GET.get('device_id')

    if not device_id:
        messages.error(request, 'Unable to identify device. Please refresh the page.')
        target_url = reverse('posts:home')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = target_url
            return response
        return redirect('posts:home')

    # Propagate device_id onto request object so signals use it accurately
    request.device_id = device_id
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
        target_url = reverse('posts:home')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = target_url
            return response
        return redirect('posts:home')

    import time
    from django.utils import timezone
    from django.utils.http import http_date
    from django.conf import settings
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

    # 1. Save current user's session in DeviceAccount so it stays persistent on this device
    if request.user.is_authenticated and hasattr(request, 'session') and request.session.session_key:
        current_da = DeviceAccount.objects.filter(
            user=request.user,
            device_id=hashed_device_id
        ).first()
        if current_da:
            current_da.session_key = request.session.session_key
            current_da.last_used = timezone.now()
            current_da.save(update_fields=['session_key', 'last_used'])

    # 2. Check if target user has an existing valid session in django_session
    target_session = None
    if device_account.session_key:
        store = SessionStore(session_key=device_account.session_key)
        if store.exists(device_account.session_key):
            session_data = store.load()
            if session_data.get(SESSION_KEY) == str(target_user.pk):
                target_session = store

    # 3. If no existing valid session, create a new session directly for target_user
    if not target_session:
        target_session = SessionStore()
        target_session[SESSION_KEY] = target_user._meta.pk.value_to_string(target_user)
        target_session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        target_session[HASH_SESSION_KEY] = target_user.get_session_auth_hash()
        target_session.save()

    # 4. Update the target device account with the persistent session key
    target_session.modified = True
    target_session.save()
    device_account.session_key = target_session.session_key
    device_account.last_used = timezone.now()
    device_account.save(update_fields=['session_key', 'last_used'])

    # 5. Attach target user and target session to request
    request.user = target_user
    request.session = target_session

    messages.success(request, f'Switched to {target_user.get_full_name() or target_user.username}')

    # Determine target URL
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        target_url = next_url
    else:
        target_url = reverse('posts:home')

    # For HTMX requests, issue HX-Redirect to force a clean full-page reload
    if request.headers.get('HX-Request'):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = target_url
    else:
        response = redirect(target_url)

    # 6. Explicitly set session cookie on response to switch the browser session directly
    max_age = target_session.get_expiry_age()
    expires_time = time.time() + max_age
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        target_session.session_key,
        max_age=max_age,
        expires=http_date(expires_time),
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
        secure=settings.SESSION_COOKIE_SECURE or None,
        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )

    return response



@login_required
def get_device_accounts_view(request):
    """
    Get list of accounts associated with the current device.
    Returns JSON for the account switcher modal.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to get device ID from headers first, then query parameters
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        device_id = request.GET.get('device_id')
    logger.info(f'[Device Accounts] Request from user {request.user.username}, device_id: {device_id[:8] if device_id else "None"}...')

    if not device_id:
        logger.warning('[Device Accounts] No device ID in request headers or query parameters')
        return JsonResponse({'accounts': [], 'error': 'Device not identified'})

    hashed_device_id = hash_device_id(device_id)
    logger.info(f'[Device Accounts] Hashed device ID: {hashed_device_id[:16]}...')

    # Ensure the current logged-in user is associated with this device
    try:
        current_da, created = DeviceAccount.objects.get_or_create(
            user=request.user,
            device_id=hashed_device_id,
            defaults={'session_key': request.session.session_key}
        )
        if not created and not current_da.session_key and request.session.session_key:
            current_da.session_key = request.session.session_key
            current_da.save(update_fields=['session_key', 'last_used'])
    except Exception as e:
        logger.warning(f'[Device Accounts] Could not link current user: {e}')

    device_accounts = DeviceAccount.objects.filter(
        device_id=hashed_device_id
    ).select_related('user').order_by('-last_used')
    
    logger.info(f'[Device Accounts] Found {device_accounts.count()} device accounts')

    accounts_data = []
    for da in device_accounts:
        try:
            pic_url = da.user.profile_pic.url if (da.user.profile_pic and hasattr(da.user.profile_pic, 'url')) else '/static/images/default_pic1.jpg'
            accounts_data.append({
                'id': da.user.id,
                'username': da.user.username,
                'full_name': da.user.get_full_name() or str(da.user),
                'profile_pic': pic_url,
                'last_used': da.last_used.isoformat() if da.last_used else None,
                'is_current': da.user.id == request.user.id
            })
        except Exception as e:
            logger.error(f'[Device Accounts] Error processing account {da.user.username}: {e}')

    logger.info(f'[Device Accounts] Returning {len(accounts_data)} accounts')
    return JsonResponse({'accounts': accounts_data})



@login_required
def remove_account_from_device_view(request, user_id):
    """
    Remove an account from the current device's account list.
    Does not delete the user account, just removes the device association.
    """
    # Try to get device ID from headers first (HTMX/fetch requests)
    device_id = request.headers.get('X-Device-ID')

    # Fallback to POST or GET parameters
    if not device_id:
        device_id = request.POST.get('device_id') or request.GET.get('device_id')

    is_json = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.headers.get('HX-Request') == 'true' or
        'application/json' in request.headers.get('Accept', '')
    )

    if not device_id:
        if is_json:
            return JsonResponse({'status': 'error', 'message': 'Unable to identify device.'}, status=400)
        messages.error(request, 'Unable to identify device.')
        return redirect('posts:home')

    hashed_device_id = hash_device_id(device_id)

    # Prevent removing the current account
    if user_id == request.user.id:
        if is_json:
            return JsonResponse({'status': 'error', 'message': 'Cannot remove the currently active account.'}, status=400)
        messages.error(request, 'Cannot remove the currently active account.')
        return redirect('posts:home')

    try:
        device_account = DeviceAccount.objects.get(
            user_id=user_id,
            device_id=hashed_device_id
        )
        device_account.delete()
        if is_json:
            return JsonResponse({'status': 'success', 'message': 'Account removed from device.'})
        messages.success(request, 'Account removed from device.')
    except DeviceAccount.DoesNotExist:
        if is_json:
            return JsonResponse({'status': 'error', 'message': 'Account not found on this device.'}, status=404)
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

    # Get like count and check if current user liked the photo
    from .models import UserProfilePhotoLike
    like_count = UserProfilePhotoLike.objects.filter(
        profile_user=profile_user,
        photo_type=photo_type
    ).count()

    is_liked = UserProfilePhotoLike.objects.filter(
        user=request.user,
        profile_user=profile_user,
        photo_type=photo_type
    ).exists()

    context = {
        'profile_user': profile_user,
        'photo_url': photo_url,
        'photo_type': photo_type,
        'photo_title': photo_title,
        'is_own_profile': is_own_profile,
        'like_count': like_count,
        'is_liked': is_liked,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'users/partials/profile_photo_fullscreen_navigation_partial.html', context)
    return render(request, 'users/profile_photo_fullscreen.html', context)


@login_required
def toggle_profile_photo_like(request, username, photo_type):
    """
    Toggle like status for a user's profile or cover photo.
    API endpoint for fullscreen photo view.
    """
    profile_user = get_object_or_404(User, username=username)

    # Validate photo type
    if photo_type not in ['profile', 'cover']:
        return JsonResponse(
            {'detail': 'Invalid photo type. Must be profile or cover.'},
            status=400
        )

    # Check if photo exists
    if photo_type == 'cover' and not profile_user.cover_photo:
        return JsonResponse(
            {'detail': 'This user does not have a cover photo.'},
            status=404
        )

    from .models import UserProfilePhotoLike
    like, created = UserProfilePhotoLike.objects.get_or_create(
        user=request.user,
        profile_user=profile_user,
        photo_type=photo_type
    )

    likes_count = UserProfilePhotoLike.objects.filter(
        profile_user=profile_user,
        photo_type=photo_type
    ).count()

    if created:
        return JsonResponse(
            {'detail': 'Photo liked.', 'likes_count': likes_count},
            status=201
        )
    else:
        like.delete()
        return JsonResponse(
            {'detail': 'Photo unliked.', 'likes_count': likes_count},
            status=200
        )


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
        summary="Like or unlike user photo",
        description="Toggle like status for a user's profile or cover photo",
        responses={200: {"detail": "Photo unliked.", "likes_count": 0}, 201: {"detail": "Photo liked.", "likes_count": 1}}
    )
    @action(detail=True, methods=['post'], url_path='photos/(?P<photo_type>[^/.]+)/like')
    def photo_like(self, request, pk=None, photo_type=None):
        """Like or unlike a user's profile or cover photo"""
        profile_user = self.get_object()

        # Validate photo type
        if photo_type not in ['profile', 'cover']:
            return Response(
                {'detail': 'Invalid photo type. Must be profile or cover.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if photo exists
        if photo_type == 'cover' and not profile_user.cover_photo:
            return Response(
                {'detail': 'This user does not have a cover photo.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from .models import UserProfilePhotoLike
        like, created = UserProfilePhotoLike.objects.get_or_create(
            user=request.user,
            profile_user=profile_user,
            photo_type=photo_type
        )

        likes_count = UserProfilePhotoLike.objects.filter(
            profile_user=profile_user,
            photo_type=photo_type
        ).count()

        if created:
            return Response(
                {'detail': 'Photo liked.', 'likes_count': likes_count},
                status=status.HTTP_201_CREATED
            )
        else:
            like.delete()
            return Response(
                {'detail': 'Photo unliked.', 'likes_count': likes_count},
                status=status.HTTP_200_OK
            )

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
        summary="Update audio preference",
        description="Update the authenticated user's audio preference for video playback (muted or unmuted)",
        responses={200: {"audio_preference": "string"}, 400: {"error": "message"}}
    )
    @action(detail=False, methods=['patch'])
    def update_audio_preference(self, request):
        """Update audio preference"""
        audio_pref = request.data.get('audio_preference')
        if audio_pref not in ['muted', 'unmuted']:
            return Response(
                {'error': 'Invalid audio preference. Must be muted or unmuted.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.audio_preference = audio_pref
        request.user.save()
        return Response({'audio_preference': audio_pref})

    @extend_schema(
        summary="Update appearance preferences",
        description="Update the authenticated user's appearance preferences (theme, font_size, language, font_family, font_style)",
        responses={200: {"theme_preference": "string", "font_size_preference": "string", "language_preference": "string", "font_family_preference": "string", "font_style_preference": "string"}, 400: {"error": "message"}}
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

        # Update font family preference if provided
        if 'font_family_preference' in data:
            font_family = data['font_family_preference']
            valid_font_families = ['default', 'inter', 'roboto', 'ibm_plex_serif', 'manrope', 'playfair_display', 'romanesco', 'story_script', 'poppins', 'lora', 'merriweather', 'dancing_script', 'great_vibes', 'parisienne', 'satisfy', 'cookie', 'italianno', 'tangerine']
            if font_family not in valid_font_families:
                return Response(
                    {'error': 'Invalid font family preference. Must be one of: ' + ', '.join(valid_font_families)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.font_family_preference = font_family
            updated_fields['font_family_preference'] = font_family

        # Update font style preference if provided
        if 'font_style_preference' in data:
            font_style = data['font_style_preference']
            if font_style not in ['normal', 'italic']:
                return Response(
                    {'error': 'Invalid font style preference. Must be normal or italic.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.font_style_preference = font_style
            updated_fields['font_style_preference'] = font_style

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
