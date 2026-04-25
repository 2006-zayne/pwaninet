from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from courses.models import Course, Year, Unit
from posts.models import Post, Like, Comment, CommentLike
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from notifications.models import Notifications
from users.models import User, Follow
from core.forms import PwaniSignupForm, PostForm, ProfileUpdateForm, GroupForm
from django.contrib import messages
from django.db.models import Q, Count
import random
from django.http import JsonResponse, HttpResponse
from posts.services.comment_service import build_comments_context, handle_add_comment_request, toggle_comment_like_for_user
from posts.services.feed_service import build_home_feed_context
from posts.services.post_service import toggle_post_like_for_user, create_post_for_user
from notifications.services.notification_service import build_notifications_context, build_unread_notification_html, get_cached_unread_count, invalidate_unread_count_cache, mark_single_notification_as_read, create_notification


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
    return render(request, 'register.html', {'form': form})


def load_years(request):
    course_id = request.GET.get('course')
    years = Year.objects.filter(course_id=course_id).order_by('level')
    return render(request, 'partials/year_options.html', {'years': years})


@login_required
def home_view(request):
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    context = build_home_feed_context(request.user, page=page)
    
    # If HTMX requests the home feed (e.g. when clearing search), return the inner content
    if request.headers.get('HX-Request') and not request.GET.get('q'):
        return render(request, 'partials/home_content.html', context)

    # For HTMX infinite scroll: render only the posts partial
    if request.headers.get('HX-Request'):
        return render(request, 'partials/post_list.html', context)

    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    return render(request, 'home.html', context)


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile_user).order_by('-created_at')
    is_following = Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    followers_count = profile_user.follower_relationships.count()
    following_count = profile_user.following_relationships.count()
    total_likes = Like.objects.filter(post__author=profile_user).count()
    return render(request, 'profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'total_likes': total_likes,
    })


@login_required
def update_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('users:profile', username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'update_profile.html', {'form': form})


@login_required
def notifications_list(request):
    context = build_notifications_context(request.user, mark_read=True)
    context['unread_notifications_count'] = 0
    return render(request, 'notifications.html', context)


@login_required
def unread_notification_count(request):
    html = build_unread_notification_html(request.user)
    return HttpResponse(html)


@login_required
def mark_notification_as_read(request, notif_id):
    mark_single_notification_as_read(request.user, notif_id)
    from notifications.services.notification_service import build_notifications_context
    context = build_notifications_context(request.user, mark_read=False)
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    response = render(request, 'partials/notification_list.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
def mark_all_as_read(request):
    if request.method == 'POST':
        Notifications.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        invalidate_unread_count_cache(request.user.id)
    return HttpResponse('')


@login_required
def create_post_view(request):
    group_id = request.GET.get('group_id')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            create_post_for_user(form, request.user, request.FILES, group_id=group_id)
            messages.success(request, 'Post created successfully.')
            return redirect('posts:home')
    else:
        form = PostForm(user=request.user)
    return render(request, 'create_post.html', {'form': form})


@login_required
def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    show_all = request.GET.get('show_all') == '1'
    context = build_comments_context(post, request.user, show_all_comments=show_all)
    context['is_liked'] = post.is_liked_by(request.user)
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    return render(request, 'post_detail.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        handle_add_comment_request(request, post)
    return redirect('posts:post_details', post_id=post_id)


@login_required
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    result = toggle_comment_like_for_user(comment, request.user)
    liked_comment_ids = result.get('liked_comment_ids', set())
    return render(request, 'partials/comment_item.html', {
        'comment': comment,
        'liked_comment_ids': liked_comment_ids,
    })


@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    result = toggle_post_like_for_user(post, request.user)
    return render(request, 'partials/like_button.html', {
        'post': result['post'],
        'is_liked': result['is_liked'],
        'like_count': result['like_count'],
    })


@login_required
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
        Notifications.objects.create(
            recipient=target, sender=request.user,
            notification_type=Notifications.FOLLOW,
            msg='started following you.'
        )
        invalidate_unread_count_cache(target.id)
        is_following = True

    # Invalidate friend suggestions cache
    from users.services.friend_suggestion_service import invalidate_friend_suggestions_cache
    invalidate_friend_suggestions_cache(request.user.id)

    follower_count = target.follower_relationships.count()

    if request.headers.get('HX-Request'):
        # Return HTML partial based on which button triggered the request
        template = 'partials/follow_button_profile.html'
        if request.GET.get('source') == 'recruit':
            template = 'partials/follow_button_recruit.html'

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
    from core.services.friend_suggestion_service import get_friend_suggestions_for_user
    suggestions = get_friend_suggestions_for_user(request.user, limit=5)
    return render(request, 'partials/suggestions.html', {'suggestions': suggestions})


@login_required
def post_likers_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    likers = User.objects.filter(like__post=post) if hasattr(User, "like_set") else User.objects.filter(id__in=post.likes.values_list("user_id", flat=True))
    return render(request, 'partials/likers_modal_content.html', {'likers': likers})


@login_required
def unit_posts_view(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    posts = Post.objects.filter(unit=unit).select_related('author', 'unit').order_by('-date')
    liked_post_ids = set(Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True))
    return render(request, 'unit_detail.html', {
        'unit': unit,
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
    })


@login_required
def groups_dashboard(request):
    user_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.APPROVED)
    pending_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.PENDING)
    all_groups = Group.objects.all().annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))).order_by('-member_count')
    user_group_ids = set(user_groups.values_list('id', flat=True))
    pending_group_ids = set(pending_groups.values_list('id', flat=True))
    return render(request, 'groups_dashboard.html', {
        'user_groups': user_groups,
        'all_groups': all_groups,
        'user_group_ids': user_group_ids,
        'pending_group_ids': pending_group_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
    })


@login_required
def groups_detail_view(request, group_id):
    from groups.services.group_service import build_group_detail_context
    from django.db.models import Count, Q
    group = get_object_or_404(Group.objects.annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))), id=group_id)
    query = request.GET.get('search_user', '')
    context = build_group_detail_context(request.user, group, query)
    liked_post_ids = set(Like.objects.filter(user=request.user, post__in=context['posts']).values_list('post_id', flat=True))
    context['liked_post_ids'] = liked_post_ids
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    return render(request, 'groups_detail.html', context)


@login_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            Membership.objects.create(group=group, user=request.user, role=MembershipRole.ADMIN, status=MembershipStatus.APPROVED)
            messages.success(request, f'Squad "{group.name}" created successfully.')
            return redirect('groups:groups_detail', group_id=group.id)
    else:
        form = GroupForm()
    return render(request, 'create_group.html', {'form': form})


@login_required
def toggle_group_membership(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check official group restrictions
    if group.is_official and group.course and group.year:
        if request.user.course != group.course or request.user.year != group.year:
            messages.error(request, 'You can only join official groups that match your course and year.')
            return redirect('groups:groups_detail', group_id=group_id)
    
    # Check if already has membership
    existing_membership = Membership.objects.filter(group=group, user=request.user).first()
    
    if existing_membership:
        existing_membership.delete()
        messages.success(request, f'You left {group.name}.')
    else:
        # For official groups, membership needs approval (pending status)
        # For community groups, auto-approve
        status = MembershipStatus.PENDING if group.is_official else MembershipStatus.APPROVED
        membership = Membership.objects.create(group=group, user=request.user, status=status)
        if status == MembershipStatus.APPROVED:
            messages.success(request, f'You joined {group.name}!')
            # Send welcome notification
            create_notification(
                recipient=request.user,
                sender=request.user,
                notification_type=Notifications.GROUP_APPROVED,
                msg=f'Welcome to {group.name}! You can now contribute to the group.',
                group=group
            )
            invalidate_unread_count_cache(request.user.id)
        else:
            messages.info(request, f'Your request to join {group.name} is pending approval.')
            # Send request confirmation notification - use group creator as sender
            sender_user = group.created_by if group.created_by else request.user
            create_notification(
                recipient=request.user,
                sender=sender_user,
                notification_type=Notifications.GROUP_REQUEST,
                msg=f'Your request to join {group.name} has been sent. You will be notified when it is accepted.',
                group=group
            )
            invalidate_unread_count_cache(request.user.id)
    
    return redirect('groups:groups_detail', group_id=group_id)


@login_required
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin (creator or has admin membership)
    is_admin = (group.created_by == request.user) or Membership.objects.filter(
        group=group, 
        user=request.user, 
        role=MembershipRole.ADMIN, 
        status=MembershipStatus.APPROVED
    ).exists()
    
    if not is_admin:
        messages.error(request, 'Only admins can edit this group.')
        return redirect('groups:groups_detail', group_id=group_id)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Squad updated.')
            return redirect('groups:groups_detail', group_id=group_id)
    else:
        form = GroupForm(instance=group)
    return render(request, 'create_group.html', {'form': form, 'group': group})


@login_required
def invite_to_group(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    target = get_object_or_404(User, id=user_id)
    if not Membership.objects.filter(group=group, user=target).exists():
        create_notification(
            recipient=target,
            sender=request.user,
            notification_type=Notifications.INVITE,
            msg=f'invited you to join {group.name}.',
            group=group
        )
        messages.success(request, f'Invite sent to {target.username}.')
    return redirect('groups:groups_detail', group_id=group_id)


@login_required
def respond_to_invite(request, notif_id, action):
    notif = get_object_or_404(Notifications, id=notif_id, recipient=request.user)
    if notif.group:
        if action == 'accept':
            Membership.objects.create(group=notif.group, user=request.user, status=MembershipStatus.APPROVED)
            messages.success(request, f'You joined {notif.group.name}!')
        else:
            messages.info(request, 'Invite declined.')
    notif.delete()
    return redirect('notifications:notifications')

@login_required
def search_view(request):
    from posts.queries.search_queries import search_users, search_groups, get_user_groups
    query = request.GET.get('q', '')
    
    users = search_users(query, request.user)
    groups = search_groups(query)
    user_groups = get_user_groups(request.user)
    
    context = {
        'query': query,
        'users': users,
        'groups': groups,
        'user_groups': user_groups,
        'unread_notifications_count': get_cached_unread_count(request.user),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'partials/search_results_inner.html', context)

    return render(request, 'search_results.html', context)
